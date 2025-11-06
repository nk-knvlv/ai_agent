import pollinations
from json import loads
from browser import Browser

base_prompt = '''
Ты - автономный AI-агент, который управляет веб-браузером для выполнения задач пользователя. Ты можешь использовать следующие функции для взаимодействия с браузером:

Функции:
- open_url(url): открывает указанный URL.
- click(selector): кликает на элемент, найденный по селектору.
- type(selector, text): вводит текст в поле ввода.
- select_dropdown(selector, option): выбирает опцию в выпадающем списке.
- get_text(selector): возвращает текст элемента.
- wait_for_element(selector): ждет появления элемента.
- execute_script(script): выполняет JavaScript код.
- switch_to_window(window_handle): переключается на указанное окно.
- close_window(): закрывает текущее окно.
- go_back(): навигация назад.
- go_forward(): навигация вперед.
- refresh(): обновляет страницу.
- press_key(key): нажимает клавишу.
- scroll_to(selector): прокручивает до элемента.
- hover(selector): наводит курсор на элемент.
- drag_and_drop(source_selector, target_selector): перетаскивает элемент.
- accept_alert(): принимает алерт.
- dismiss_alert(): отклоняет алерт.

Ты получишь задачу от пользователя и текущее состояние страницы (в виде HTML).
Ты должен анализировать HTML, чтобы понять, какие элементы присутствуют на странице,
и решить, какое действие выполнить next.

Если запрос пользователя не является задачей, верни {
  "thought": "",
  "action": {
    "name": "type",
    "args": {
      "selector": "#username",
      "text": "my_username"
    }
  }
}

Ты должен отвечать в формате JSON, который содержит два поля:
- "thought": строка, в которой ты объясняешь, что ты видишь на странице и почему ты выбираешь следующее действие.
- "action": объект, описывающий действие. Если ты решил выполнить функцию, то укажи имя функции и аргументы. Если задача завершена, то в "action" укажи success.

Пример ответа:
{
  "thought": "Я вижу страницу входа. Мне нужно ввести логин и пароль. Сначала я введу логин в поле с id 'username'.",
  "action": {
    "name": "type",
    "args": {
      "selector": "#username",
      "text": "my_username"
    }
  }
}

Когда задача будет выполнена, ты должен вернуть:
{
  "thought": "Задача выполнена. Пользователь успешно вошел в систему.",
  "action": null
}

Ты должен быть осторожен и не выполнять действия, которые могут навредить. 
Если ты не уверен в селекторе, используй get_text или другие функции,
чтобы получить больше информации о элементе.

Начни!'''


class Agent:
    task_status: str
    user_task_request: str
    browser_functional: dict | None

    def __init__(self):
        self.task_status = "Not specified"
        self.task = None
        self.model = pollinations.Text(system=base_prompt)
        self.browser_functional = None

    async def run(self, page, browser_functional):
        # self.user_task_request = input('Какую задачу я должен выполнить? :')
        self.user_task_request = "Закажи помидоры на самокате"
        self.browser_functional = browser_functional
        llm_answer = loads(await self.model.Async(
            "вот запрос пользователя:" + self.user_task_request + "согласно этому запросу Верни url сайта на котором должна быть решена задача"))
        action = llm_answer['action']['name']
        url = llm_answer['action']['args']['url']

        if llm_answer == 'error':
            raise Exception('error')

        await self.browser_functional[action](page, url)

        while self.task_status != 'success':
            # получить верстку
            print(await self.browser_functional['get_page_html'](page))
            break
            # сформировать промпт (задача, история, текущее состояние)
            # отправить промпт модели и отправить ответ
            # парсит на предмет вызова функции
            # выполняет функцию и обновляет историю
            # если модель считает что задача завершена, выходит из цикла
