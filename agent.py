from http.client import HTTPException
from urllib.error import HTTPError
from asyncio import get_event_loop
import pollinations
from json import loads, dumps
from browser import Browser
import inspect


class Agent:
    """
    Класс ИИ агента выполняющего задания в браузере
    """

    def __init__(self, browser):
        """
        Определяем правила игры
        """
        self.browser = browser
        conditions = self.get_conditions(browser)
        self.model = pollinations.Text(system=conditions)

        self.loop = get_event_loop()

        self.context = {
            "current_url": '',
            "user_task": '',
            "current_goal": '',
            "step_history": []
        }

    async def wake_up(self):
        await self.browser.launch()
        await self.start_chat()

    async def start_chat(self):
        """
        Запускает интерактивный чат с пользователем.

        Чат продолжается до получения команды 'off' или критической ошибки.
        """
        print('Какое задание мне выполнить?\n')

        try:
            while True:
                try:
                    # Асинхронный ввод вместо блокирующего input()
                    message = await self.async_input()

                    if message.lower().strip() == 'off':
                        print("Завершение работы...")
                        self.browser.stop()
                        break

                    if not message.strip():
                        continue  # Пропускаем пустые сообщения

                    possible_task = await self.try_extract_task(message)
                    if possible_task:
                        print(f"Как я понял: {possible_task}")
                        await self.entrust(possible_task)
                    else:
                        print("Пожалуйста, отправьте четкое задание для выполнения")

                except KeyboardInterrupt:
                    print("\nЗавершение по команде пользователя...")
                    break
                except Exception as e:
                    print(f"Ошибка при обработке сообщения: {e}")
                    continue

        except Exception as e:
            print(f"Критическая ошибка в чате: {e}")
        finally:
            print("Чат завершен")


    async def async_input(self) -> str:
        """
        Асинхронная версия input().

        Returns:
            str: Введенная пользователем строка
        """
        return await self.loop.run_in_executor(None, input, "> ")

    async def try_extract_task(self, message: str) -> str | None:
        """
        Пытается извлечь задачу из сообщения пользователя.

        Args:
            message: Сообщение от пользователя

        Returns:
            str: Переформулированная задача если найдена
            None: Если задача не найдена или произошла ошибка
        """
        prompted_message = f"""
            Ты - анализатор задач. Определи, является ли сообщение пользователя задачей для ИИ-ассистента.
        
            КРИТЕРИИ ЗАДАЧИ:
            - Конкретное действие (найти, скачать, проанализировать, сравнить)
            - Выполнимо через браузер
            - Имеет четкую цель
        
            ФОРМАТ ОТВЕТА ТОЧНО В ОДНОЙ СТРОКЕ:
            [ЗАДАЧА|НЕТ]| |описание
        
            Примеры:
            ЗАДАЧА| Найти рецепт пасты карбонара
            НЕТ| Это приветствие, а не задача
            ЗАДАЧА| Сравнить цены на iPhone в разных магазинах
        
            Сообщение: "{message}"
            """

        try:
            response = await self.send(prompted_message)
            response = response.strip()

            # Разбираем ответ по формату
            if "|" in response:
                parts = response.split("|", 1)
                if len(parts) == 2:
                    status, task_text = parts[0].strip(), parts[1].strip()

                    if status == "ЗАДАЧА" and task_text:
                        return task_text

            return None

        except Exception as e:
            print(f"Ошибка при извлечении задачи из '{message}': {e}")
            return None

    async def entrust(self, task):
        """
        Поручает ИИ выполнить конкретное задание
        """
        self.context['user_task'] = task

        plan = await self.get_plan(task)
        print('составляю план')
        print(plan)
        #
        # for goal in eval(plan):
        #     print(f'выполняю {goal}')
        #     self.context['current_goal'] = goal
        #     self.step_status = False
        #     tries = 0
        #     while not self.step_status:
        #         try:
        #             low_prompt = await self.get_low_prompt(page=page)
        #             symb_count = len(low_prompt)
        #             low_actions_dict = loads(await self.get_llm_answer(
        #                 low_prompt
        #             ))
        #             self.update_context(low_actions_dict['context'])
        #             if 'thought' in low_actions_dict:
        #                 print(low_actions_dict['thought'])
        #
        #             if low_actions_dict['actions'] == 'success':
        #                 self.step_status = True
        #                 self.history = ''
        #                 break
        #             await self.carry_out(actions)
        #         except HTTPError as e:
        #             if tries < 4:
        #                 tries += 1
        #                 continue
        #             else:
        #                 raise e

    async def send(self, message) -> str:
        """
        Обрабатывает сообщение от пользователя
        """
        print("думаю...")
        answer = await self.model.Async(message)
        return answer

    async def carry_out(self, actions):
        for move in actions:
            print(f'выполняю {move}')
            move['parameters']['page'] = page
            self.context['step_history'].append(f"action - {move}")
            func = self.browser_functional[move['name']]
            if inspect.iscoroutinefunction(func):
                returned = await func(**move['parameters'])
            else:
                returned = func(**move['parameters'])
            if returned:
                self.history += f"action returned value - {returned}"

    def update_context(self, context):
        for el, val in context.items():
            self.context[el] = val

    def get_conditions(self, browser):
        available_actions = self.get_class_func_description(browser)
        conditions = f'''
            Ты - автономный AI-агент, который управляет веб-браузером для выполнения задач пользователя.
            
            Ты получишь задачу от пользователя и класс для взаимодействия с браузером
            
            Доступные действия:
            {available_actions}                
            
            Начинаешь ты с about:blank страницы
            Ты должен анализировать HTML, чтобы понять, какие элементы присутствуют на странице,
            и решить, какое действие выполнить next.
            Ты должен быть осторожен и не выполнять действия, которые могут навредить.
            Ты можешь выполнять поиск в поисковых системах. 
            Если действие подразумевает данные или подтверждения которые знает только человек,
            например выбор адреса или внесение данных оплаты,
            тебе нужно передать управление человеку.
            '''
        return conditions

    async def get_plan(self, task):
        plan_making_prompt = f"""
                Пользователь хочет: {task}.
    
                Разбей эту задачу на высокоуровневые односложные, но информативные шаги. Например:
    
                Открыть сайт mail.ru
                
                Прочитать письма
                
                Если спам то пометить как спам
    
                Выведи только список python, без дополнительных объяснений, на языке запроса.
            """

        return await self.send(plan_making_prompt)

    @staticmethod
    def filter_interactive_elements(accessibility_tree):
        """Фильтрует accessibility tree, оставляя только интерактивные элементы"""

        interactive_roles = {
            'button', 'link', 'textbox', 'searchbox', 'checkbox',
            'radio', 'slider', 'combobox', 'listbox', 'menu',
            'menuitem', 'tab', 'switch', 'option', 'search'
        }

        interactive_elements = []

        def traverse_and_filter(node, path=""):
            if not node:
                return

            # Проверяем, является ли элемент интерактивным
            is_interactive = (
                    node.get('role') in interactive_roles or
                    node.get('focused') is True or
                    node.get('focusable') is True or
                    node.get('clickable') is True or
                    # Элементы с обработчиками событий
                    any(key in node for key in ['onclick', 'onkeypress', 'onkeydown']) or
                    # Элементы форм
                    node.get('role') == 'textbox' and node.get('value') or
                    # Карточки товаров (часто имеют роль article или region с кликабельностью)
                    (node.get('role') in ['article', 'region'] and node.get('clickable'))
            )

            # Дополнительные проверки для специфических элементов
            has_shopping_indicators = any(indicator in str(node).lower() for indicator in [
                'товар', 'product', 'карточка', 'card', 'купить', 'buy',
                'цена', 'price', 'корзина', 'cart', 'заказ', 'order'
            ])

            if is_interactive or has_shopping_indicators:
                element_info = {
                    'role': node.get('role'),
                    'name': node.get('name', ''),
                    'description': node.get('description', ''),
                    'value': node.get('value', ''),
                    'focused': node.get('focused', False),
                    'focusable': node.get('focusable', False),
                    'path': path
                }
                interactive_elements.append(element_info)

            # Рекурсивно обходим детей
            for i, child in enumerate(node.get('children', [])):
                child_path = f"{path}/{node.get('role', 'root')}[{i}]"
                traverse_and_filter(child, child_path)

        traverse_and_filter(accessibility_tree)
        return interactive_elements

    async def get_low_prompt(self, page):
        self.context['current_url'] = page.url
        accessibility_tree = await self.browser_functional['get_accessibility_tree'](page)
        page_state_ino = self.filter_interactive_elements(accessibility_tree)
        prompt = f"""
                    Текущее состояние страницы:
                    {dumps(page_state_ino)}
                    контекст:    
                    {dumps(self.context)}            
                    
                    Учитывая контекст, проверь выполнена ли задача, если нет то
                    Сгенерируй последовательность действий для выполнения текущего шага. 
                    
                    Ты должен отвечать в формате JSON, который содержит два поля:
                    - "thought": строка, в которой ты объясняешь, что ты видишь на странице и почему ты выбираешь следующее действие.
                    - "actions": объект, описывающий действия. Если ты решил выполнить функцию, то укажи имя функции и аргументы. Если задача завершена, то в "actions" укажи success.
                    - "context": объект, описывающий контекст. Если ты в действии перешел на другой сайт соответствующе поменяй контекст. Указывай только те поля которые поменялись.
                    Пример ответа:
                    {{
                        "thought": "я понимаю что нахожусь не на том сайте где пользователь просил решить задачу, надо перейти на нужный",
                        "actions":{{
                                    {{
                                        "name": "open_url",
                                        "parameters": {{
                                                "url": "https://samokat.ru",
                                        }}
                                    }},
                                    {{
                                        "name": "type",
                                        "parameters": {{
                                                "selector": "input[.search]",
                                                "text": "мед",
                                        }}
                                    }}
                                }},
                        "context":{{
                            "current_url": "https://samokat.ru",
                        }}        
                    }}
                    Если ты не уверен в селекторе, используй get_element_text или другие функции,
                    чтобы получить больше информации о элементе.
                    Важно: используй только доступные действия.
                    """
        return prompt

    @staticmethod
    def get_class_func_description(cls: type) -> str:
        """
        Получает описание всех методов класса.

        Args:
            cls: Класс для анализа

        Returns:
            str: JSON-строка с информацией о всех методах класса
        """
        functions_info = []

        # Получаем все методы класса
        for func_name, func in inspect.getmembers(cls, predicate=inspect.isfunction):
            # Пропускаем приватные и защищенные методы
            if func_name.startswith('_'):
                continue

            # Получаем сигнатуру
            signature = inspect.signature(func)
            parameters = []

            for param_name, param in signature.parameters.items():
                if param_name in ('self', 'cls'):
                    continue

                param_info = {"name": param_name}

                if param.annotation != inspect.Parameter.empty:
                    param_info["type"] = str(param.annotation)

                if param.default != inspect.Parameter.empty:
                    param_info["default"] = str(param.default)

                parameters.append(param_info)

            # Получаем документацию
            docstring = func.__doc__
            description = ""
            if docstring:
                description = docstring.strip().split('\n')[0].strip()

            func_info = {
                "name": func_name,
                "description": description,
                "parameters": parameters,
                "return_type": str(signature.return_annotation),
                "full_docstring": docstring.strip() if docstring else ""
            }

            functions_info.append(func_info)

        return dumps(functions_info, ensure_ascii=False, indent=2)

    # сформировать промпт (задача, история, текущее состояние)
    # отправить промпт модели и отправить ответ

    # парсит на предмет вызова функции
    # выполняет функцию и обновляет историю
    # если модель считает что задача завершена, выходит из цикла
