import asyncio
from playwright.async_api import Page, Locator, async_playwright
from typing import Optional, Coroutine
import base64
from PIL import Image
import io
import os


class Browser:
    def __init__(self):
        self.browser_app = None
        self.playwright = None
        self.page = None
        self.model = None
        self.page_context = []

    async def launch(self, model):
        # Создаем объект без контекстного менеджера
        self.playwright = async_playwright()
        self.model = model
        # Вручную запускаем
        playwright_obj = await self.playwright.start()
        self.browser_app = await playwright_obj.chromium.launch(
            headless=False,  # Показываем браузер
            channel="chrome",  # Используем установленный Chrome
        )
        self.page = await self.new_page()
        return self.page

    async def stop(self):
        self.browser_app.close()
        await self.playwright.stop()

    async def new_page(self):
        return await self.browser_app.new_page()

    def get_page_url(self):
        """Получает Url текущей страницы

        Args:
            page: Объект страницы Playwright

        Returns:
            str: Url текущей страницы в виде строки
        """
        return self.page.url

    async def open_url(self, url: str) -> None:
        """Переходит по указанному URL

        Args:
            page (Page): Объект страницы Playwright
            url (str): URL для перехода (например, "https://example.com")

        Returns:
            None
        """
        await self.page.goto(url, wait_until='load')
        print('ожидаем загрузки страницы')
        await self.wait(10000)

    async def click(self, selector: str) -> None:
        """Кликает на элемент по CSS-селектору

        Args:
            page (Page): Объект страницы Playwright
            selector (str): CSS-селектор элемента для клика (например, ".button", "#submit")

        Returns:
            None
        """
        await self.page.click(selector)

    async def type_into(self, selector: str, text: str) -> None:
        """Вводит текст в поле ввода по CSS-селектору

        Args:
            page (Page): Объект страницы Playwright
            selector (str): CSS-селектор поля ввода (например, "input[name='search']")
            text (str): Текст для ввода

        Returns:
            None
        """
        await self.page.fill(selector, text)

    async def wait(self, time):
        """Ожидает указанное количество миллисекунд

        Args:
            page: Объект страницы Playwright
            time (float): Время ожидания в миллисекундах

        Returns:
            None

        Note:
            Используйте для искусственных задержек. Для ожидания элементов используйте wait_for_element
        """
        await self.page.wait_for_timeout(time)

    async def press(self, selector, key):
        """Нажимает клавишу на элементе или странице

        Args:
            page: Объект страницы Playwright
            selector (str): CSS-селектор элемента. Если None, нажимает на всей странице
            key (str): Название клавиши (например, "Enter", "Escape", "Tab", "ArrowDown")

        Returns:
            None
        """
        await self.page.press(selector, key)

    def _glimpse_scan(self, selectors):
        """
        Быстрое сканирование важных элементов на странице
        """
        glimpse_data = {}

        for selector in selectors:
            element = self.page.query_selector(selector)
            if element:
                # Получаем базовую информацию об элементе
                glimpse_data[selector] = {
                    'text': element.text_content()[:100] if element.text_content() else None,
                    'visible': element.is_visible(),
                    'attributes': element.evaluate("el => el.attributes.length"),
                    'type': element.get_attribute('type') if element.get_attribute('type') else 'element'
                }
            else:
                glimpse_data[selector] = None

        return glimpse_data

    async def _analyze_dom_structure(self, root_selector: str = 'body', current_depth: int = 0):
        """Рекурсивный анализ DOM-структуры с глубиной до 5 уровней"""

        if current_depth >= 5:
            return {"depth_exceeded": True}

        try:
            structure = await self.page.locator(root_selector).first.evaluate('''(element, current_depth) => {
                const result = {
                    selector: element.tagName.toLowerCase(),
                    attributes: {},
                    text: element.textContent ? element.textContent.trim().slice(0, 100) : null,
                    visible: element.offsetWidth > 0 && element.offsetHeight > 0,
                    focus: document.activeElement === element,
                    children: {},
                    children_count: {}
                };

                // Собираем основные атрибуты
                for (let attr of element.attributes) {
                    result.attributes[attr.name] = attr.value;
                }

                // Анализируем непосредственных детей
                const children = element.children;
                const childrenByTag = {};

                for (let child of children) {
                    const tagName = child.tagName.toLowerCase();
                     // Пропускаем нежелательные теги
                    if (tagName === 'script' || tagName === 'iframe' || tagName === 'next-route-announcer') {
                        continue;
                    }
                    
                    if (!childrenByTag[tagName]) {
                        childrenByTag[tagName] = [];
                    }
                    childrenByTag[tagName].push(child);
                }

                // Сохраняем количество детей по тегам
                for (let tagName in childrenByTag) {
                    result.children_count[tagName] = childrenByTag[tagName].length;
                }
                
                // Для каждого типа тега сохраняем всех детей
                for (let tagName in childrenByTag) {
                    if (childrenByTag[tagName].length > 0) {
                        // Создаем массив для всех элементов этого тега
                        result.children[tagName] = [];
                        
                        for (let child of childrenByTag[tagName]) {
                            const childData = {
                                selector: tagName,
                                attributes: {},
                                focus: document.activeElement === child,
                                text: child.textContent ? child.textContent.trim().slice(0, 50) : null,
                                visible: child.offsetWidth > 0 && child.offsetHeight > 0,
                                children_count: child.children.length
                            };
                
                            // Собираем атрибуты для каждого ребенка
                            for (let attr of child.attributes) {
                                childData.attributes[attr.name] = attr.value;
                            }
                            
                            result.children[tagName].push(childData);
                        }
                    }
                }

                return result;
            }''', current_depth)

            # Рекурсивно анализируем детей следующего уровня
            for child_tag in list(structure['children'].keys()):
                child_selector = f"{root_selector} > {child_tag}"
                for index in range(0,len(structure['children'][child_tag])):
                    if structure['children'][child_tag][index]['children_count'] > 0:
                        try:
                            child_structure = await self._analyze_dom_structure(child_selector, current_depth + 1)
                            structure['children'][child_tag][index]['children'] = child_structure['children']
                        except Exception as e:
                            structure['children'][child_tag][index]['children'] = {'error': str(e)}

            return structure

        except Exception as e:
            return {"error": str(e), "selector": root_selector, "depth": current_depth}

    async def get_element_selector_by_description(self, description):
        print('начинаю поиск элемента по описанию')
        depth = 0
        selector = None
        root_selector = 'body'
        search_stack = ['body']
        while not selector and depth < 60:
            print(search_stack)
            print(f'ищем в {root_selector}')
            depth += 1

            void_list = []
            print('получаю упрощенную структуру DOM')
            body_structure = await self._analyze_dom_structure(root_selector=root_selector)
            prompt = f"""
            Анализ DOM структуры для поиска элемента

            ЦЕЛЕВОЙ ЭЛЕМЕНТ: {description}

            ДОСТУПНАЯ СТРУКТУРА:
            {body_structure}
            
            Стек поиска:
            {search_stack}
            
            Список уже проверенных селекторов:
            {void_list}

            ПРОЦЕСС:
            1. Сканируй структуру сверху вниз
            2. Отмечай потенциальные совпадения
            3. Если ты не нашел нужный селектор, но есть предположение где он находится запрашивай уточнение через INTERESTING
            4. Выбирай лучший вариант или запрашивай уточнения
            5. Конечный курсор должен соответствовать описанию, например если это кнопка то по ней можно будет кликнуть

            КРИТЕРИИ ВЫБОРА:
            - Семантические теги (button, input, a)
            - Значимые классы/ID (submit, btn, button)
            - Текстовое содержание
            - Структурное положение

            Отвечай только предложенными шаблонами, без дополнительных описаний
            ВОЗМОЖНЫЕ ОТВЕТЫ:
            "СЕЛЕКТОР: [селектор который точно соответствует описанию] | THAT'S IS"
            "СЕЛЕКТОР: [селектор] | INTERESTING:вопрос"
            "СЕЛЕКТОР: [селектор к которому хочешь вернуться]| CAN'T FIND: элемент не обнаружен в текущей структуре" 
            
            Если ты отправил cant find это вернет тебя на уровень выше, и добавит селектор в void list

            """
            temp = len(prompt)
            response = await self.model.send(prompt)
            # send to model and ask for a selector we are looking for

            # or selector for build another structure and resend
            if "СЕЛЕКТОР:" in response and "|" in response:
                parts = response.split("|")
                selector_part = parts[0].replace("СЕЛЕКТОР:", "").strip()
                info_part = parts[1].strip()

                if "THAT'S IS" in info_part:
                    print(f'найден нужный селектор {selector_part} ')
                    selector = selector_part
                    self.page_context.append({f'{description}':f'{selector}'})
                elif "INTERESTING" in info_part:
                    print(f'нужны уточнения {selector_part} ')
                    root_selector = selector_part
                    search_stack.append(selector_part)
                    continue
                elif "CAN'T FIND" in info_part:
                    print(f'исключаю из поиска {root_selector} ')
                    void_list.append(root_selector)
                    search_stack.pop()
                    root_selector = selector_part
                    search_stack.append(root_selector)

        return selector

    async def get_page_html(self):
        """Получает полный HTML-код текущей страницы

        Args:
            page: Объект страницы Playwright

        Returns:
            str: HTML-код страницы в виде строки
        """
        return await self.page.content()
