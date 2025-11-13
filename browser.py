import asyncio
from playwright.async_api import Page, Locator, async_playwright
from typing import Optional, Coroutine


class Browser:
    def __init__(self):
        self.browser_app = None
        self.playwright = None

    async def launch(self):
        # Создаем объект без контекстного менеджера
        self.playwright = async_playwright()

        # Вручную запускаем
        playwright_obj = await self.playwright.start()
        self.browser_app = await playwright_obj.chromium.launch(
            headless=False,  # Показываем браузер
            channel="chrome",  # Используем установленный Chrome
        )
        return await self.new_page()


    async def stop(self):
        self.browser_app.close()
        await self.playwright.stop()

    async def new_page(self):
        self.browser_app.current_page = await self.browser_app.new_page()
        return self.browser_app.current_page

    @staticmethod
    async def get_accessibility_tree(page):
        """Получает дерево доступности (Accessibility Tree) страницы

        Args:
            page: Объект страницы Playwright

        Returns:
            dict: Дерево доступности со структурой элементов

        Note:
            Содержит только semantic информацию: роли, имена, состояния
            Намного легче полного HTML
        """
        return await page.accessibility.snapshot()

    # @staticmethod
    # async def get_page_html(page):
    #     """Получает полный HTML-код текущей страницы
    #
    #     Args:
    #         page: Объект страницы Playwright
    #
    #     Returns:
    #         str: HTML-код страницы в виде строки
    #     """
    #     return await page.content()

    @staticmethod
    def get_page_url(page):
        """Получает Url текущей страницы

        Args:
            page: Объект страницы Playwright

        Returns:
            str: Url текущей страницы в виде строки
        """
        return page.url

    @staticmethod
    async def open_url(page: Page, url: str) -> None:
        """Переходит по указанному URL

        Args:
            page (Page): Объект страницы Playwright
            url (str): URL для перехода (например, "https://example.com")

        Returns:
            None
        """
        await page.goto(url)

    @staticmethod
    async def click(page: Page, selector: str) -> None:
        """Кликает на элемент по CSS-селектору

        Args:
            page (Page): Объект страницы Playwright
            selector (str): CSS-селектор элемента для клика (например, ".button", "#submit")

        Returns:
            None
        """
        await page.click(selector)

    @staticmethod
    async def type(page: Page, selector: str, text: str) -> None:
        """Вводит текст в поле ввода по CSS-селектору

        Args:
            page (Page): Объект страницы Playwright
            selector (str): CSS-селектор поля ввода (например, "input[name='search']")
            text (str): Текст для ввода

        Returns:
            None
        """
        await page.fill(selector, text)

    @staticmethod
    async def wait_for_element(page: Page, selector: str, timeout: Optional[float] = None) -> None:
        """Ожидает появление элемента на странице

        Args:
            page (Page): Объект страницы Playwright
            selector (str): CSS-селектор ожидаемого элемента
            timeout (float, optional): Время ожидания в миллисекундах. По умолчанию используется таймаут страницы

        Returns:
            None
        """
        await page.wait_for_selector(selector, timeout=timeout)

    @staticmethod
    async def wait(page, time):
        """Ожидает указанное количество миллисекунд

        Args:
            page: Объект страницы Playwright
            time (float): Время ожидания в миллисекундах

        Returns:
            None

        Note:
            Используйте для искусственных задержек. Для ожидания элементов используйте wait_for_element
        """
        await page.wait_for_timeout(time)

    @staticmethod
    async def press(page, selector, key):
        """Нажимает клавишу на элементе или странице

        Args:
            page: Объект страницы Playwright
            selector (str): CSS-селектор элемента. Если None, нажимает на всей странице
            key (str): Название клавиши (например, "Enter", "Escape", "Tab", "ArrowDown")

        Returns:
            None
        """
        await page.press(selector, key)

    @staticmethod
    async def get_element_text(page: Page, selector: str) -> str:
        """Получает текстовое содержимое элемента

        Args:
            page (Page): Объект страницы Playwright
            selector (str): CSS-селектор элемента

        Returns:
            str: Текстовое содержимое элемента
        """
        return await page.text_content(selector)
    #
    # @staticmethod
    # async def type_and_press_enter(page: Page, selector: str, text: str) -> None:
    #     """Вводит текст в поле и нажимает Enter для подтверждения
    #
    #     Args:
    #         page (Page): Объект страницы Playwright
    #         selector (str): CSS-селектор поля ввода
    #         text (str): Текст для ввода и поиска
    #
    #     Returns:
    #         None
    #     """
    #     await page.fill(selector, text)
    #     await page.press(selector, 'Enter')
