import pytest

from pages.todo_page import TodoPage


@pytest.mark.initial_input_validation
@pytest.mark.test_case_id("TC-001")
def test_tc_001(page, base_url):

    todo_page = TodoPage(page)

    todo_page.navigate(base_url)

    input_field = todo_page.todo_input

    assert input_field.is_visible(), (
        "Todo input field is not visible."
    )

    assert input_field.is_enabled(), (
        "Todo input field is not enabled."
    )

    assert input_field.get_attribute("readonly") is None, (
        "Todo input field is readonly."
    )

    assert input_field.get_attribute("placeholder") == 'What needs to be done?', (
        "Incorrect placeholder text."
    )

    assert input_field.input_value() == "", (
        "Input field should initially be empty."
    )

