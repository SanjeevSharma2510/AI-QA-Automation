import pytest

from pages.todo_page import TodoPage


@pytest.mark.boundary_input
@pytest.mark.test_case_id("TC-003")
def test_tc_003(page, base_url):

    todo_page = TodoPage(page)

    todo_page.navigate(base_url)

    test_values = [
        "A",
        "B" * 255,
        "C" * 1000
    ]

    for value in test_values:

        todo_page.add_todo(value)

        assert todo_page.get_todo_count() > 0, (
            "Todo item was not created."
        )

        actual_text = todo_page.get_todo_text(-1)

        assert actual_text == value, (
            f"Todo text mismatch for input length {len(value)}."
        )

        assert todo_page.todo_input.input_value() == "", (
            "Input field was not cleared after submission."
        )

