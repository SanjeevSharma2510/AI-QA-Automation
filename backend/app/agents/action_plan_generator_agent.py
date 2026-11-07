import argparse
import json
import re
from pathlib import Path

from backend.app.ai.gemini_client import GeminiClient


PROJECT_ROOT = Path(__file__).resolve().parents[3]

REVIEWED_CASES_FILE = (
    PROJECT_ROOT
    / "generated"
    / "test_cases"
    / "reviewed_test_cases.json"
)

ACTION_PLANS_DIR = (
    PROJECT_ROOT
    / "generated"
    / "action_plans"
)

SUPPORTED_ACTIONS = {
    "navigate",
    "fill",
    "click",
    "press",
    "select",
    "assert_visible",
    "assert_text",
    "assert_attribute",
    "assert_value",
    "assert_count"
}

SUPPORTED_LOCATORS = {
    "id",
    "css",
    "xpath",
    "text",
    "placeholder",
    "role",
    "label"
}


class ActionPlanGeneratorAgent:

    def __init__(self):

        self.gemini = GeminiClient()

        ACTION_PLANS_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

    def load_test_case(self, test_case_id):

        if not REVIEWED_CASES_FILE.exists():

            raise FileNotFoundError(
                f"Reviewed test cases file not found: "
                f"{REVIEWED_CASES_FILE}"
            )

        with open(
            REVIEWED_CASES_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        cases = (
            data
            if isinstance(data, list)
            else data.get("test_cases", [])
        )

        for case in cases:

            if case.get("test_case_id") == test_case_id:

                if case.get("review_status") != "approved":

                    raise ValueError(
                        f"{test_case_id} is not approved."
                    )

                if case.get("execution_status") != "passed":

                    raise ValueError(
                        f"{test_case_id} has not passed execution."
                    )

                return case

        raise ValueError(
            f"Test case not found: {test_case_id}"
        )

    def get_application_guidance(self, case):
        """
        Return application-specific guidance only when
        the supplied test case identifies a known application.
        """

        case_context = json.dumps(
            {
                "module": case.get("module"),
                "preconditions": case.get("preconditions", []),
                "test_steps": case.get("test_steps", []),
                "expected_results": case.get("expected_results", [])
            }
        ).lower()

        if "demo.playwright.dev/todomvc" in case_context:
            return """
        APPLICATION-SPECIFIC GUIDANCE: TODOMVC
    
        1. Todo input:
           Prefer placeholder:
           What needs to be done?
    
        2. Todo item labels:
           Prefer CSS:
           .todo-list li label
    
        3. Todo item count:
           Prefer CSS:
           .todo-list li
    
        4. For the second Todo item:
           .todo-list li:nth-child(2) label
    
        5. Avoid page-wide text locators for short Todo values.
    
        6. For boundary-length inputs, verify the complete
           saved text, not just the item count.
    
        7. Use repeated-text objects when appropriate:
           {"text": "B", "repeat": 255}
    
        8. Apply these selectors only to TodoMVC.
        """

            return """
        APPLICATION-SPECIFIC GUIDANCE:
    
        No predefined application-specific selectors are available.
    
        Analyze the supplied test case, preconditions and evidence
        to identify the actual application elements.
    
        Do not assume a particular website, framework, page
        structure, element ID, CSS selector or URL.
    
        Use only selectors supported by the supplied evidence.
        """

        def build_prompt(self, case):

            test_case_data = {
                "test_case_id": case["test_case_id"],
                "module": case.get("module"),
                "scenario_name": case["scenario_name"],
                "scenario_type": case.get("scenario_type"),
                "preconditions": case.get("preconditions", []),
                "test_steps": case.get("test_steps", []),
                "expected_results": case.get("expected_results", []),
                "evidence": case.get("evidence", [])
            }

            application_guidance = self.get_application_guidance(case)

            return f"""
    You are an expert Playwright automation engineer.

    Convert the supplied approved manual test case into
    a reliable, structured browser action plan.

    Your objective is to generate reusable browser actions
    that can execute against different websites.

    TEST CASE:

    {json.dumps(test_case_data, indent=4)}

    SUPPORTED ACTIONS:

    1. navigate: action, url
    2. fill: action, locator, value
    3. click: action, locator
    4. press: action, locator, key
    5. select: action, locator, value
    6. assert_visible: action, locator
    7. assert_text: action, locator, expected
    8. assert_attribute: action, locator, attribute, expected
    9. assert_value: action, locator, expected
    10. assert_count: action, locator, expected

    SUPPORTED LOCATOR STRATEGIES:

    - id
    - css
    - xpath
    - text
    - placeholder
    - role
    - label

    LOCATOR FORMAT:

    {{
        "strategy": "placeholder",
        "value": "Enter username"
    }}

    ROLE LOCATOR FORMAT:

    {{
        "strategy": "role",
        "value": "button",
        "name": "Login"
    }}

    APPLICATION-SPECIFIC GUIDANCE:

    {application_guidance}

    ==================================================
    GENERIC LOCATOR RULES
    ==================================================

    1. Prefer stable and unique locators.

    2. Use the following priority when supported by evidence:

       - ID
       - data-testid or stable CSS attributes
       - placeholder
       - label
       - role with accessible name
       - specific CSS selector
       - XPath
       - text when appropriate

    3. Never invent element IDs, attributes or selectors.

    4. Avoid generic text locators that can match
       multiple elements.

    5. Avoid short text values as page-wide locators.

    6. Avoid broad selectors such as body, *, div or p
       unless specifically required.

    7. Scope locators to the relevant container
       whenever possible.

    8. Use actual application evidence to identify elements.

    9. Do not assume every website has the same page structure.

    10. Do not reuse application-specific selectors
        on unrelated websites.

    ==================================================
    GENERAL ACTION PLAN RULES
    ==================================================

    1. Return only valid JSON.

    2. Do not return Markdown or explanations.

    3. Include test_case_id and scenario_name.

    4. Include an actions array.

    5. Preserve the original test intent.

    6. Do not invent URLs, credentials, buttons or fields.

    7. Use the URL from the supplied preconditions.

    8. Include sufficient assertions to verify
       the expected results.

    9. Do not perform destructive actions unless
       explicitly authorized.

    10. Do not use unsupported actions.

    11. Do not omit important validation steps.

    12. For absent HTML boolean attributes,
        use null as the expected value.

    13. For repeated text, use this format:

    {{
        "text": "B",
        "repeat": 255
    }}

    14. Repeat count must be between 0 and 10000.

    15. For press actions, use the key property:

    {{
        "action": "press",
        "locator": {{
            "strategy": "placeholder",
            "value": "Enter task"
        }},
        "key": "Enter"
    }}

    16. Never use value instead of key for press actions.

    17. Maintain the correct sequence of browser actions.

    18. Every action must use a locator corresponding
        to the intended element.

    19. Generate only actions necessary to satisfy
        the test case.

    20. Validate the complete expected outcome,
        not merely that an action executed successfully.

    EXPECTED JSON STRUCTURE:

    {{
        "test_case_id": "{case['test_case_id']}",
        "scenario_name": "{case['scenario_name']}",
        "actions": [
            {{
                "action": "navigate",
                "url": "https://example.com"
            }},
            {{
                "action": "assert_visible",
                "locator": {{
                    "strategy": "id",
                    "value": "username"
                }}
            }}
        ]
    }}
    """

    def validate_value(self, value, field_name):

        if isinstance(value, dict):

            if set(value.keys()) != {"text", "repeat"}:

                raise ValueError(
                    f"Invalid repeated value in {field_name}."
                )

            if not isinstance(value["text"], str):

                raise ValueError(
                    f"Repeated text must be a string: {field_name}"
                )

            if (
                not isinstance(value["repeat"], int)
                or isinstance(value["repeat"], bool)
                or not 0 <= value["repeat"] <= 10000
            ):

                raise ValueError(
                    f"Invalid repeat count: {field_name}"
                )

        elif not isinstance(value, str):

            raise ValueError(
                f"{field_name} must be a string or repeat object."
            )

    def validate_plan(self, plan, case):

        if not isinstance(plan, dict):

            raise ValueError(
                "Generated action plan must be a JSON object."
            )

        if plan.get("test_case_id") != case["test_case_id"]:

            raise ValueError(
                "Generated test_case_id does not match the source case."
            )

        if not isinstance(plan.get("actions"), list):

            raise ValueError(
                "Action plan must contain an actions array."
            )

        if not plan["actions"]:

            raise ValueError(
                "Generated action plan contains no actions."
            )

        for index, action in enumerate(
            plan["actions"],
            start=1
        ):

            if not isinstance(action, dict):

                raise ValueError(
                    f"Action {index} must be a JSON object."
                )

            action_type = action.get("action")

            if action_type not in SUPPORTED_ACTIONS:

                raise ValueError(
                    f"Unsupported action at position {index}: "
                    f"{action_type}"
                )

            if action_type == "navigate":

                if not isinstance(action.get("url"), str):

                    raise ValueError(
                        f"Action {index}: navigate requires a URL."
                    )

                if not re.match(
                    r"^https?://",
                    action["url"],
                    re.IGNORECASE
                ):

                    raise ValueError(
                        f"Action {index}: invalid navigation URL."
                    )

                continue

            locator = action.get("locator")

            if not isinstance(locator, dict):

                raise ValueError(
                    f"Action {index}: locator is required."
                )

            strategy = locator.get("strategy")
            value = locator.get("value")

            if strategy not in SUPPORTED_LOCATORS:

                raise ValueError(
                    f"Action {index}: unsupported locator strategy "
                    f"{strategy}."
                )

            if not isinstance(value, str) or not value.strip():

                raise ValueError(
                    f"Action {index}: locator value is missing."
                )

            if action_type in {"fill", "select"}:

                self.validate_value(
                    action.get("value"),
                    f"action {index} value"
                )

            elif action_type == "press":

                if not isinstance(action.get("key"), str):

                    raise ValueError(
                        f"Action {index}: key is required."
                    )

            elif action_type == "assert_text":

                self.validate_value(
                    action.get("expected"),
                    f"action {index} expected"
                )

            elif action_type == "assert_attribute":

                if not isinstance(action.get("attribute"), str):

                    raise ValueError(
                        f"Action {index}: attribute is required."
                    )

                if (
                    "expected" not in action
                    or not (
                        isinstance(action["expected"], str)
                        or action["expected"] is None
                    )
                ):

                    raise ValueError(
                        f"Action {index}: expected must be a string "
                        "or null."
                    )

            elif action_type == "assert_value":

                self.validate_value(
                    action.get("expected"),
                    f"action {index} expected"
                )

            elif action_type == "assert_count":

                expected = action.get("expected")

                if (
                    not isinstance(expected, int)
                    or isinstance(expected, bool)
                    or expected < 0
                ):

                    raise ValueError(
                        f"Action {index}: expected count must be "
                        "a non-negative integer."
                    )

        return plan

    def generate(self, test_case_id):

        print(
            f"\nLoading approved test case: {test_case_id}"
        )

        case = self.load_test_case(test_case_id)

        prompt = self.build_prompt(case)

        print("\nGenerating action plan with Gemini...")

        response = self.gemini.generate_json(prompt)

        try:

            plan = json.loads(response)

        except json.JSONDecodeError as exc:

            raise ValueError(
                f"Gemini returned invalid JSON: {exc}"
            ) from exc

        plan = self.validate_plan(
            plan,
            case
        )

        output_file = (
            ACTION_PLANS_DIR
            / f"{test_case_id}_ai.json"
        )

        with open(
            output_file,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                plan,
                file,
                indent=4,
                ensure_ascii=False
            )

        print("\nAction plan generated successfully.")

        print(f"Saved to: {output_file}")

        print(
            f"Total actions generated: {len(plan['actions'])}"
        )

        return plan


def main():

    parser = argparse.ArgumentParser(
        description="Generate Playwright action plans using Gemini."
    )

    parser.add_argument(
        "--test-case-id",
        required=True,
        help="Approved test case ID"
    )

    args = parser.parse_args()

    agent = ActionPlanGeneratorAgent()

    agent.generate(args.test_case_id)


if __name__ == "__main__":

    main()