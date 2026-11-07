
class ActionPlanExecutor:

    def __init__(self, page):

        self.page = page

    def resolve_value(self, value):

        if isinstance(value, dict):

            if "text" in value and "repeat" in value:

                return value["text"] * value["repeat"]

        return value

    def get_locator(self, config):

        strategy = config["strategy"]
        value = config["value"]

        if strategy == "id":
            return self.page.locator(f"#{value}")

        if strategy == "css":
            return self.page.locator(value)

        if strategy == "xpath":
            return self.page.locator(f"xpath={value}")

        if strategy == "text":
            return self.page.get_by_text(value)

        if strategy == "placeholder":
            return self.page.get_by_placeholder(value)

        if strategy == "label":
            return self.page.get_by_label(value)

        if strategy == "role":

            return self.page.get_by_role(
                value,
                name=config.get("name")
            )

        raise ValueError(
            f"Unsupported locator strategy: {strategy}"
        )

    def execute(self, action):

        action_type = action["action"]

        if action_type == "navigate":

            self.page.goto(action["url"])

            return

        locator = self.get_locator(
            action["locator"]
        )

        if action_type == "fill":

            locator.fill(
                self.resolve_value(action["value"])
            )

        elif action_type == "click":

            locator.click()

        elif action_type == "press":
            locator.press(action["key"])
        elif action_type == "select":
            locator.select_option(action["value"])

        elif action_type == "assert_visible":

            assert locator.is_visible(), (
                "Expected element to be visible."
            )

        elif action_type == "assert_text":

            expected = self.resolve_value(
                action["expected"]
            )

            actual = locator.inner_text()

            assert actual == expected, (
                f"Text mismatch. Expected length: {len(expected)}; "
                f"Actual length: {len(actual)}"
            )

        elif action_type == "assert_attribute":

            actual = locator.get_attribute(
                action["attribute"]
            )

            expected = action["expected"]

            assert actual == expected, (
                f"Attribute '{action['attribute']}' mismatch. "
                f"Expected: {expected!r}; Actual: {actual!r}"
            )

        elif action_type == "assert_value":

            expected = self.resolve_value(
                action["expected"]
            )

            actual = locator.input_value()

            assert actual == expected, (
                f"Input value mismatch. "
                f"Expected: {expected!r}; Actual: {actual!r}"
            )

        elif action_type == "assert_count":

            actual = locator.count()

            expected = action["expected"]

            assert actual == expected, (
                f"Element count mismatch. "
                f"Expected: {expected}; Actual: {actual}"
            )

        else:

            raise ValueError(
                f"Unsupported action: {action_type}"
            )

    def execute_plan(self, plan):

        for index, action in enumerate(
            plan["actions"],
            start=1
        ):

            print(
                f"Executing action {index}: "
                f"{action['action']}"
            )

            self.execute(action)
