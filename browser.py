import asyncio
from playwright.async_api import Page, Locator, async_playwright
from typing import Optional, Coroutine


class Browser:
    functional: dict

    def __init__(self, agent):
        self.ai_agent = agent
        self.functional = {'run': self.run()}

    async def run(self):
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=False,  # Показываем браузер
                channel="chrome",  # Используем установленный Chrome
                slow_mo=1000
            )
            self.ai_agent.run()
            #
            # page = await browser.new_page()
            # await page.goto("самокат")
            # print(await page.title())
            # await browser.close()

    @staticmethod
    async def get_page_html(page):
        return await page.content()

    # # 1. Открытие URL
    # async def open_url(page: Page, url: str) -> None:
    #     await page.goto(url)
    #
    # # 2. Клик по элементу
    # async def click(page: Page, selector: str) -> None:
    #     await page.click(selector)
    #
    # # 3. Ввод текста
    # async def type(page: Page, selector: str, text: str) -> None:
    #     await page.fill(selector, text)
    #
    # # 4. Выбор опции в выпадающем списке
    # async def select_dropdown(page: Page, selector: str, option: str) -> None:
    #     await page.select_option(selector, option)
    #
    # # 5. Получение текста элемента
    # async def get_text(page: Page, selector: str) -> str:
    #     return await page.text_content(selector)
    #
    # # 6. Ожидание элемента
    # async def wait_for_element(page: Page, selector: str, timeout: Optional[float] = None) -> None:
    #     await page.wait_for_selector(selector, timeout=timeout)
    #
    # # 7. Выполнение JavaScript
    # async def execute_script(page: Page, script: str) -> object:
    #     return await page.evaluate(script)
    #
    # # 8. Переключение на вкладку/окно
    # async def switch_to_window(page: Page, window_handle: Page) -> None:
    #     # В Playwright работа с страницами через объект context
    #     # window_handle должен быть объектом Page
    #     page.context.pages  # Доступ ко всем открытым страницам
    #     # Логика переключения должна быть реализована через управление страницами
    #     raise NotImplementedError("Используйте page.context.pages для управления вкладками")
    #
    # # 9. Закрытие текущего окна
    # async def close_window(page: Page) -> None:
    #     await page.close()
    #
    # # 10. Навигация назад
    # async def go_back(page: Page) -> None:
    #     await page.go_back()
    #
    # # 11. Навигация вперед
    # async def go_forward(page: Page) -> None:
    #     await page.go_forward()
    #
    # # 12. Обновление страницы
    # async def refresh(page: Page) -> None:
    #     await page.reload()
    #
    # # 13. Нажатие клавиши
    # async def press_key(page: Page, key: str) -> None:
    #     await page.keyboard.press(key)
    #
    # # 14. Прокрутка к элементу
    # async def scroll_to(page: Page, selector: str) -> None:
    #     await page.locator(selector).scroll_into_view_if_needed()
    #
    # # 15. Ховер над элементом
    # async def hover(page: Page, selector: str) -> None:
    #     await page.hover(selector)
    #
    # # 16. Перетаскивание элемента
    # async def drag_and_drop(page: Page, source_selector: str, target_selector: str) -> None:
    #     await page.drag_and_drop(source_selector, target_selector)
    #
    # # 17. Принять алерт
    # async def accept_alert(page: Page) -> None:
    #     await page.on("dialog", lambda dialog: dialog.accept())
    #
    # # 18. Отклонить алерт
    # async def dismiss_alert(page: Page) -> None:
    #     await page.on("dialog", lambda dialog: dialog.dismiss())
