
class ActionExecutor:
    """
    Reusable Playwright action executor.

    Supports common browser interactions without application-specific
    scenario names.
    """

    def __init__(self, page):
        self.page = page

    def execute(self, action):
        action_type = action.get("action")

        if action_type == "navigate":
            return self.navigate(action)

        elif action_type == "fill":
            return self.fill(action)

        elif action_type == "click":
            return self.click(action)

        elif action_type == "press":
            return self.press(action)

        elif action_type == "select":
            return self.select(action)

        elif action_type == "assert_visible":
            return self.assert_visible(action)

        elif action_type == "assert_text":
            return self.assert_text(action)

        elif action_type == "assert_attribute":
            return self.assert_attribute(action)

        elif action_type == "assert_value":
            return self.assert_value(action)

        elif action_type == "assert_count":
            return self.assert_count(action)
        else:
            raise ValueError(
                f"Unsupported browser action: {action_type}"
            )

    def get_locator(self, locator_config):
        strategy = locator_config["strategy"]
        value = locator_config["value"]

        if strategy == "id":
            return self.page.locator(f"#{value}")

        elif strategy == "css":
            return self.page.locator(value)

        elif strategy == "xpath":
            return self.page.locator(f"xpath={value}")

        elif strategy == "text":
            return self.page.get_by_text(value, exact=True)

        elif strategy == "placeholder":
            return self.page.get_by_placeholder(value)

        elif strategy == "role":
            return self.page.get_by_role(
                value,
                name=locator_config.get("name")
            )

        elif strategy == "label":
            return self.page.get_by_label(value)

        else:
            raise ValueError(
                f"Unsupported locator strategy: {strategy}"
            )

    def navigate(self, action):
        url = action["url"]
        self.page.goto(url)

        return {
            "action": "navigate",
            "status": "passed",
            "url": self.page.url
        }

    def fill(self, action):

        locator = self.get_locator(action["locator"])

        value = self.resolve_value(
            action.get("value", "")
        )

        locator.fill(value)

        return {
            "action": "fill",
            "status": "passed",
            "value_length": len(value)
        }

    def click(self, action):
        locator = self.get_locator(action["locator"])
        locator.click()

        return {
            "action": "click",
            "status": "passed"
        }

    def press(self, action):
        locator = self.get_locator(action["locator"])
        key = action["key"]

        locator.press(key)

        return {
            "action": "press",
            "status": "passed",
            "key": key
        }

    def select(self, action):
        locator = self.get_locator(action["locator"])
        value = action["value"]

        locator.select_option(value)

        return {
            "action": "select",
            "status": "passed",
            "value": value
        }

    def assert_visible(self, action):
        locator = self.get_locator(action["locator"])

        assert locator.is_visible(), (
            f"Element is not visible: {action['locator']}"
        )

        return {
            "action": "assert_visible",
            "status": "passed"
        }

    def assert_text(self, action):

        locator = self.get_locator(action["locator"])

        expected = self.resolve_value(
            action["expected"]
        )

        actual = locator.inner_text()

        assert actual == expected, (
            f"Text mismatch. Expected length: {len(expected)}, "
            f"Actual length: {len(actual)}"
        )

        return {
            "action": "assert_text",
            "status": "passed",
            "expected_length": len(expected),
            "actual_length": len(actual)
        }

    def assert_attribute(self, action):
        locator = self.get_locator(action["locator"])

        attribute = action["attribute"]
        expected = action["expected"]

        actual = locator.get_attribute(attribute)

        assert actual == expected, (
            f"Attribute mismatch for '{attribute}'. "
            f"Expected: {expected}, Actual: {actual}"
        )

        return {
            "action": "assert_attribute",
            "status": "passed",
            "attribute": attribute,
            "actual": actual
        }

    def assert_value(self, action):
        locator = self.get_locator(action["locator"])
        expected = action["expected"]

        actual = locator.input_value()

        assert actual == expected, (
            f"Input value mismatch. Expected: {expected}, Actual: {actual}"
        )

        return {
            "action": "assert_value",
            "status": "passed",
            "actual": actual
        }

    def assert_count(self, action):

        locator = self.get_locator(action["locator"])

        expected = action["expected"]
        actual = locator.count()

        assert actual == expected, (
            f"Element count mismatch. "
            f"Expected: {expected}, Actual: {actual}"
        )

        return {
            "action": "assert_count",
            "status": "passed",
            "expected": expected,
            "actual": actual
        }

    def resolve_value(self, value):

        if isinstance(value, dict) and "repeat" in value:

            text = value["text"]
            count = value["repeat"]

            if not isinstance(text, str) or not isinstance(count, int):
                raise ValueError("Invalid repeat test data.")

            if count < 0 or count > 10000:
                raise ValueError("Repeat count must be between 0 and 10000.")

            return text * count

        return value