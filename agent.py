from asyncio import get_event_loop
from llm import LLM
from json import dumps
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
        self.model = LLM()
        self.loop = get_event_loop()

        self.context = {
            "current_url": '',
            "user_task": '',
            "current_goal": '',
            "step_history": [],
            "page":browser.page_context
        }

    async def wake_up(self):
        await self.browser.launch(self.model)
        await self.start_chat()

    async def start_chat(self):
        """
        Запускает интерактивный чат с пользователем.

        Чат продолжается до получения команды 'off' или критической ошибки.
        """

        try:
            while True:
                try:
                    self.say('Какое задание мне выполнить?')
                    # Асинхронный ввод вместо блокирующего input()
                    message = await self.loop.run_in_executor(None, input, "> ")

                    if message.lower().strip() == 'off':
                        self.say("Завершение работы...")
                        self.browser.stop()
                        break

                    if not message.strip():
                        continue  # Пропускаем пустые сообщения

                    possible_task = await self.try_extract_task(message)
                    if possible_task:
                        await self.entrust(possible_task)
                    else:
                        self.say("Пожалуйста, отправьте четкое задание для выполнения")
                except Exception as e:
                    print(f"Ошибка при обработке сообщения: {e}")
                    continue

        except Exception as e:
            print(f"Критическая ошибка в чате: {e}")
        finally:
            print("Чат завершен")

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
                    
                    КРИТЕРИИ ЗАДАЧИ ДЛЯ ИИ:
                    - Конкретное цифровое действие (найти, проанализировать, сравнить, заказать, оформить)
                    - Может быть выполнено через браузер, приложения или с передачей контроля пользователю
                    - Имеет четкую цель
                    - старайся сразу перейти на сайт, используй поиск только если не понимаешь какой конкретно сайт нужен
                    - поисковые инпуты не всегда именно input теги, могли стилизовать div, p или textarea
                    
                    ФОРМАТ ОТВЕТА ТОЧНО В ОДНОЙ СТРОКЕ:
                    [ЗАДАЧА|НЕТ]| | описание
                    
                    Примеры:
                    ЗАДАЧА| Найти рецепт пасты карбонара
                    ЗАДАЧА| Пометь спорные письма как спам на mail
                    НЕТ| Это физическое действие, требующее человека
                    НЕТ| Это приветствие, а не задача
                    ЗАДАЧА| Сравнить цены на iPhone в разных магазинах
                    
                    Сообщение: "{message}"
            """

        try:
            self.say(f'Пытаюсь выявить задание')
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

    @staticmethod
    def say(message):
        print(f'Agent: ' + message)

    async def entrust(self, task):
        """
        Поручает ИИ выполнить конкретное задание
        """
        self.context['user_task'] = task

        self.say(f'Cоставляю план')

        plan = await self.get_plan(task)

        self.say(f'План - {plan}')
        for step in eval(plan):
            attempt = 0
            success = False

            while attempt < 4 and not success:
                try:
                    self.say(f'Выполняю - {step}')
                    self.context['current_goal'] = step
                    attempt += 1
                    self.context['page'] = self.browser.page_context
                    step_prompt = await self.get_step_prompt(page=self.browser.page)
                    response = await self.send(
                        step_prompt
                    )
                    response = eval(response)

                    self.update_context(response['context'])
                    if 'thought' in response:
                        self.say(f'Мысли - {response['thought']}')

                    if response['actions'] == 'success':
                        success = True
                        break
                    if response['actions'] == 'wait_for_the_human':
                        await self.wait_human(favour=response['thought'])
                        break

                    await self.carry_out(actions=response['actions'])

                except Exception as e:
                    print(f"Ошибка при выполнении шага {step} сообщения: {e}")
                    continue
            if not success:
                print(f"Не получилось выполнить задание за отведенные попытки")
                break

    async def send(self, message) -> str:
        """
        Обрабатывает сообщение от пользователя
        """
        self.say('Думаю...')
        await self.browser.wait(2000)
        response = await self.model.send(message)
        return response

    async def wait_human(self, favour):
        self.say(favour)
        favour_is_responding = False

        while not favour_is_responding:
            message = await self.loop.run_in_executor(None, input, "> ")
            prompt = f"""Если в сообщении пользователь подтвердил что выполнил то о чем его попросили,
             или написал что ты можешь продолжать, то отправь True, если нет отправь False
             сообщение пользователя:{message}
            """

            response = await self.model.send(prompt)
            if response == "True":
                favour_is_responding = True

    async def carry_out(self, actions):
        for action in actions:
            self.say(f'выполняю {action}')

            method = getattr(self.browser, action['name'], None)

            try:
                if inspect.iscoroutinefunction(method):
                    returned = await method(**action['parameters'])
                else:
                    returned = method(**action['parameters'])

                if returned:
                    self.context['step_history'].append(f"action returned value - {returned}")
                self.context['step_history'].append(f"action - {action}")

            except AttributeError:
                error_msg = f"Method {action['name']} not found in Browser"
                print(error_msg)
                self.context['step_history'].append(f"ERROR: {error_msg}")

            except TypeError as e:
                error_msg = f"Invalid parameters for {action['name']}: {e}"
                print(error_msg)
                self.context['step_history'].append(f"ERROR: {error_msg}")

            except Exception as e:
                error_msg = f"Unexpected error in {action['name']}: {e}"
                print(error_msg)
                self.context['step_history'].append(f"ERROR: {error_msg}")

    def update_context(self, context):
        for el, val in context.items():
            self.context[el] = val


    async def get_plan(self, task):
        plan_making_prompt = f"""
            Ты - автономный AI-агент, который управляет веб-браузером для выполнения задач пользователя.
            
            Ты получишь задачу от пользователя и класс для взаимодействия с браузером
            
            Начинаешь ты с about:blank страницы
            Ты должен анализировать HTML, чтобы понять, какие элементы присутствуют на странице,
            и решить, какое действие выполнить next.
            Ты должен быть осторожен и не выполнять действия, которые могут навредить.
            Ты можешь выполнять поиск в поисковых системах. 
            Если действие подразумевает данные или подтверждения которые знает только человек,
            например выбор адреса или внесение данных оплаты,
            тебе нужно передать управление человеку.
            
            
            Пользователь хочет: {task}.
            
            Разбей эту задачу на высокоуровневые односложные, но информативные шаги. Например:
            
            ["Открыть сайт mail.ru", "Прочитать письма", "Если спам то пометить как спам"]
            
            Верни список Python в точности таком же формате, без дополнительного текста.
            ВАЖНО: Возвращай только чистый Python-код без каких-либо обратных кавычек, маркеров кода или пояснений.
            """

        return await self.send(plan_making_prompt)

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
        for func_name, func in inspect.getmembers(cls, predicate=inspect.iscoroutinefunction):
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

            func_info = {
                "name": func_name,
                "parameters": parameters,
                "return_type": str(signature.return_annotation),
            }

            functions_info.append(func_info)

        return dumps(functions_info, ensure_ascii=False, indent=2)

    # сформировать промпт (задача, история, текущее состояние)
    # отправить промпт модели и отправить ответ

    # парсит на предмет вызова функции
    # выполняет функцию и обновляет историю
    # если модель считает что задача завершена, выходит из цикла

    async def get_step_prompt(self, page):
        self.context['current_url'] = page.url
        available_actions = self.get_class_func_description(self.browser)
        prompt = f"""
                Ты - автономный AI-агент, который управляет веб-браузером для выполнения задач пользователя.

                Учитывая контекст, проверь выполнена ли задача, если нет то сгенерируй последовательность действий для выполнения текущего шага.
                Если ты не знаешь нужный селектор для действия сначала найди его с помощью доступных методов
                
                КОМАНДА: Возвращай ТОЛЬКО данные в виде Python-словаря. НИКАКИХ обратных кавычек, НИКАКИХ маркеров json, НИКАКИХ комментариев или пояснений.
                
                СТРУКТУРА ОТВЕТА:
                {{
                    "thought": "объяснение что видишь и почему выбираешь действие",
                    "actions": [массив действий или строка],
                    "context": {{'измененные поля контекста'}}
                }}
                
                ПРАВИЛА:
                - Используй только доступные действия
                - Для авторизации/оплаты используй "wait_for_the_human"
                - Указывай в контексте только измененные поля
                
        
               
                возвращай в таком виде:
               
                - "thought": строка, в которой ты объясняешь, что ты видишь на странице и почему ты выбираешь следующее действие.
                - "actions": объект, описывающий действия. Если ты решил выполнить функцию, то укажи имя функции и аргументы. Если текущая подзадача завершена, то в "actions" вместо массива укажи строку success. 
                - "context": объект, описывающий контекст. Если ты в действии перешел на другой сайт соответствующе поменяй контекст. Указывай только те поля которые поменялись.
                
                Если подзадача это авторизация или оплата, то в "actions" вместо массива укажи строку wait_for_the_human
                            
               Пример ответа:
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

               контекст:    
               {dumps(self.context, ensure_ascii=False)} 
               
                Доступные
                действия:
                {available_actions}

               """
        return prompt
