import pytest

from pages.todo_page import TodoPage


@pytest.mark.empty_submission
@pytest.mark.test_case_id("TC-002")
def test_tc_002(page, base_url):

    todo_page = TodoPage(page)

    todo_page.navigate(base_url)

    initial_count = todo_page.get_todo_count()

    todo_page.todo_input.fill("")

    todo_page.todo_input.press("Enter")

    final_count = todo_page.get_todo_count()

    assert final_count == initial_count, (
        "An empty todo item was created."
    )

