from http.client import HTTPException
from urllib.error import HTTPError

import pollinations
from json import loads, dumps
from browser import Browser
import inspect


class Agent:
    task_status: bool
    user_task: str
    browser_functional: dict | None

    def __init__(self):
        self.task_status = False
        self.step_status = False
        self.task = None
        self.model = None
        self.browser_functional = None
        self.context = {
            "current_url": None,
            "current_goal": None,
            "step_history": []
        }

    async def run(self, browser_functional, page):
        self.user_task = input('Какую задачу я должен выполнить? :')
        self.context['user_task'] = self.user_task

        # доступный llm интерфейс управления браузером
        self.browser_functional = browser_functional

        base_prompt = self.get_base_prompt()
        self.model = pollinations.Text(system=base_prompt)
        plan = await self.get_plan()

        for goal in eval(plan):
            self.context['current_goal'] = goal
            self.step_status = False
            tries = 0
            while not self.step_status:
                try:
                    low_prompt = await self.get_low_prompt(page=page)
                    symb_count = len(low_prompt)
                    low_moves_dict = loads(await self.get_llm_answer(
                        low_prompt
                    ))
                    self.update_context(low_moves_dict['context'])
                    if 'thought' in low_moves_dict:
                        print(low_moves_dict['thought'])

                    if low_moves_dict['actions'] == 'success':
                        self.step_status = True
                        self.history = ''
                        break

                    for move in low_moves_dict['actions']:
                        move['parameters']['page'] = page
                        self.context['step_history'].append(f"action - {move}")
                        func = self.browser_functional[move['name']]
                        if inspect.iscoroutinefunction(func):
                            returned = await func(**move['parameters'])
                        else:
                            returned = func(**move['parameters'])
                        if returned:
                            self.history += f"action returned value - {returned}"
                except HTTPError as e:
                    if tries < 4:
                        tries += 1
                        continue
                    else:
                        raise e

    def update_context(self, context):
        for el, val in context.items():
            self.context[el] = val

    async def get_llm_answer(self, question):
        return await self.model.Async(question)

    def get_base_prompt(self):
        browser_functions = self.get_functions_info(self.browser_functional)

        base_prompt = f'''
        Доступные действия:
        {browser_functions}                

        Ты - автономный AI-агент, который управляет веб-браузером для выполнения задач пользователя.

        Ты получишь задачу от пользователя и текущее состояние страницы (в виде HTML).
        Начинаешь ты с about:blank страницы
        Ты должен анализировать HTML, чтобы понять, какие элементы присутствуют на странице,
        и решить, какое действие выполнить next.
        Ты должен быть осторожен и не выполнять действия, которые могут навредить. 
        Если действие подразумевает данные или подтверждения которые знает только человек, тебе нужно передать управление человеку.
        '''
        return base_prompt

    async def get_plan(self):
        return await self.get_llm_answer(f"""
            Пользователь хочет: {self.user_task}.

            Разбей эту задачу на высокоуровневые односложных но информативных шагов. Например:

            Открыть сайт почты.

            Прочитать сообщение.

            Если спам, пометить как спам.

            повторить пока не будут обработаны все письма.

            Выведи только список python, без дополнительных объяснений, на языке запроса.
        """)

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
                    "action":{{
                                {{
                                    "name": "open_url",
                                    "parameters": {{
                                            "url": "https://samokat.ru",
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
    def get_functions_info(functions_list):
        functions_info = []
        for func_name, func in functions_list.items():
            # Получаем имя функции
            name = func.__name__

            # Получаем параметры
            signature = inspect.signature(func)
            parameters = []
            for param_name, param in signature.parameters.items():
                # Пропускаем self и cls для методов
                if param_name in ('self', 'cls'):
                    continue
                parameters.append(param_name)

            # Создаем словарь для функции
            func_info = {
                "name": name,
                "parameters": parameters
            }
            functions_info.append(func_info)

        # Преобразуем в JSON-строку
        return dumps(functions_info, ensure_ascii=False, indent=2)

    #
    # llm_answer = loads(await self.get_llm_answer(
    #     "вот запрос пользователя:" + self.user_task + "согласно этому запросу верни url сайта на котором должна быть решена задача, находящийся в актуальном диапазоне доменов для носителя языка запроса"))
    # action = llm_answer['action']['name']
    # url = llm_answer['action']['args']['url']
    #
    # if llm_answer == 'error':
    #     raise Exception('error')
    #
    # try:
    #     await self.browser_functional[action](page, url)
    # except Exception as e:
    #     print(e)
    #
    # while llm_answer['action'] != 'null':

# получить верстку
# page_html = await self.browser_functional['get_page_html'](page)
# break

# сформировать промпт (задача, история, текущее состояние)
# отправить промпт модели и отправить ответ

# парсит на предмет вызова функции
# выполняет функцию и обновляет историю
# если модель считает что задача завершена, выходит из цикла
