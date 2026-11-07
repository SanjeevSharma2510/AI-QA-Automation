from playwright.sync_api import Page, Locator


class TodoPage:

    def __init__(self, page: Page):

        self.page = page

        self.todo_input: Locator = page.get_by_placeholder(
            'What needs to be done?'
        )

        self.todo_items: Locator = page.locator(
            ".todo-list li"
        )

    def navigate(self, base_url: str):

        self.page.goto(base_url)

    def add_todo(self, text: str):

        self.todo_input.fill(text)

        self.todo_input.press("Enter")

    def get_todo_count(self) -> int:

        return self.todo_items.count()

    def get_todo_text(self, index: int = 0) -> str:

        return self.todo_items.nth(index).inner_text()
