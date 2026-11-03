class TestCaseValidator:
    """
    Validates AI-generated test cases before saving them.
    """

    REQUIRED_FIELDS = [
        "test_case_id",
        "module",
        "scenario_name",
        "scenario_type",
        "priority",
        "preconditions",
        "test_steps",
        "expected_results",
        "source_workflow_ids",
        "evidence",
    ]

    VALID_SCENARIO_TYPES = {
        "positive",
        "negative",
        "boundary",
        "ui_validation",
    }

    VALID_PRIORITIES = {
        "high",
        "medium",
        "low",
    }

    def validate_case(self, test_case):
        errors = []

        if not isinstance(test_case, dict):
            return ["Test case must be a JSON object."]

        # Check mandatory fields.
        for field in self.REQUIRED_FIELDS:
            if field not in test_case:
                errors.append(f"Missing required field: {field}")

        if errors:
            return errors

        # Check text fields.
        text_fields = [
            "test_case_id",
            "module",
            "scenario_name",
        ]

        for field in text_fields:
            value = test_case.get(field)

            if not isinstance(value, str) or not value.strip():
                errors.append(
                    f"{field} must be a non-empty string."
                )

        # Check scenario type.
        if test_case["scenario_type"] not in self.VALID_SCENARIO_TYPES:
            errors.append(
                f"Invalid scenario_type: {test_case['scenario_type']}"
            )

        # Check priority.
        if test_case["priority"] not in self.VALID_PRIORITIES:
            errors.append(
                f"Invalid priority: {test_case['priority']}"
            )

        # Check list fields.
        list_fields = [
            "preconditions",
            "test_steps",
            "expected_results",
            "source_workflow_ids",
            "evidence",
        ]

        for field in list_fields:
            value = test_case.get(field)

            if not isinstance(value, list):
                errors.append(f"{field} must be a list.")
                continue

            if field in [
                "test_steps",
                "expected_results",
            ] and not value:
                errors.append(
                    f"{field} cannot be empty."
                )

            for index, item in enumerate(value):
                if not isinstance(item, str) or not item.strip():
                    errors.append(
                        f"{field}[{index}] must be a non-empty string."
                    )

        return errors

    def validate_all(self, test_cases):
        errors = []
        seen_ids = set()

        if not isinstance(test_cases, list):
            return ["Test cases must be provided as a list."]

        for index, test_case in enumerate(test_cases):

            case_errors = self.validate_case(test_case)

            for error in case_errors:
                errors.append(
                    f"Test case #{index + 1}: {error}"
                )

            if isinstance(test_case, dict):
                case_id = test_case.get("test_case_id")

                if case_id:
                    if case_id in seen_ids:
                        errors.append(
                            f"Duplicate test_case_id: {case_id}"
                        )
                    else:
                        seen_ids.add(case_id)

        return errors