
import json
import re
import shutil
import zipfile

from datetime import datetime, timezone
from pathlib import Path


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

FRAMEWORK_DIR = (
    PROJECT_ROOT
    / "generated"
    / "frameworks"
    / "action_plan_playwright_project"
)

ZIP_FILE = (
    PROJECT_ROOT
    / "generated"
    / "frameworks"
    / "action_plan_playwright_project.zip"
)

TESTS_DIR = FRAMEWORK_DIR / "tests"
PAGES_DIR = FRAMEWORK_DIR / "pages"
TEST_DATA_DIR = FRAMEWORK_DIR / "test_data"
ARTIFACTS_DIR = FRAMEWORK_DIR / "artifacts"


class ActionPlanFrameworkGenerator:

    def __init__(self):

        self.test_cases = []
        self.generated_plans = []

    # ==========================================
    # LOAD REVIEWED TEST CASES
    # ==========================================

    def load_approved_cases(self):

        if not REVIEWED_CASES_FILE.exists():
            raise FileNotFoundError(
                f"Reviewed cases not found: {REVIEWED_CASES_FILE}"
            )

        with open(
            REVIEWED_CASES_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        if isinstance(data, list):
            cases = data

        elif isinstance(data, dict):
            cases = data.get(
                "test_cases",
                data.get("cases", [])
            )

        else:
            raise ValueError(
                "Invalid reviewed test cases structure."
            )

        self.test_cases = [
            case for case in cases
            if (
                case.get("review_status") == "approved"
                and case.get("execution_status") == "passed"
                and case.get("execution_result", {}).get("status") == "passed"
            )
        ]

        if not self.test_cases:

            raise ValueError(
                "No eligible test cases found. "
                "Cases must be approved and successfully executed."
            )

        print(
            f"[OK] Eligible test cases: {len(self.test_cases)}"
        )

    # ==========================================
    # LOAD AND VALIDATE AI ACTION PLANS
    # ==========================================

    def load_action_plans(self):

        print("\nLoading AI-generated action plans...")

        supported_actions = {
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

        for case in self.test_cases:

            test_id = case["test_case_id"]

            plan_file = (
                ACTION_PLANS_DIR
                / f"{test_id}_ai.json"
            )

            if not plan_file.exists():

                raise FileNotFoundError(
                    f"AI action plan missing for {test_id}"
                )

            with open(
                plan_file,
                "r",
                encoding="utf-8"
            ) as file:

                plan = json.load(file)

            if plan.get("test_case_id") != test_id:

                raise ValueError(
                    f"Test case ID mismatch in {plan_file.name}"
                )

            actions = plan.get("actions")

            if not isinstance(actions, list) or not actions:

                raise ValueError(
                    f"No valid actions found in {plan_file.name}"
                )

            for index, action in enumerate(actions, start=1):

                action_type = action.get("action")

                if action_type not in supported_actions:

                    raise ValueError(
                        f"{test_id}: Unsupported action "
                        f"'{action_type}' at position {index}"
                    )

                if action_type == "navigate":

                    url = action.get("url", "")

                    if not isinstance(url, str) or not url.startswith(
                        ("http://", "https://")
                    ):

                        raise ValueError(
                            f"{test_id}: Invalid navigation URL."
                        )

                else:

                    locator = action.get("locator")

                    if not isinstance(locator, dict):

                        raise ValueError(
                            f"{test_id}: Missing locator at action {index}"
                        )

                    strategy = locator.get("strategy")

                    if strategy not in {
                        "id",
                        "css",
                        "xpath",
                        "text",
                        "placeholder",
                        "role",
                        "label"
                    }:

                        raise ValueError(
                            f"{test_id}: Unsupported locator strategy "
                            f"'{strategy}'"
                        )

                    if not locator.get("value"):

                        raise ValueError(
                            f"{test_id}: Locator value is missing."
                        )

                if action_type == "fill":

                    fill_value = action.get("value")

                    valid_string = isinstance(fill_value, str)

                    valid_repeat_object = (
                            isinstance(fill_value, dict)
                            and isinstance(fill_value.get("text"), str)
                            and isinstance(fill_value.get("repeat"), int)
                            and not isinstance(fill_value.get("repeat"), bool)
                            and 0 <= fill_value["repeat"] <= 10000
                    )

                    if not (valid_string or valid_repeat_object):
                        raise ValueError(
                            f"{test_id}: Invalid value for fill."
                        )

                if action_type == "select":
                    fill_value = action.get("value")

                    valid_string = isinstance(fill_value, str)

                    valid_repeat_object = (
                            isinstance(fill_value, dict)
                            and isinstance(fill_value.get("text"), str)
                            and isinstance(fill_value.get("repeat"), int)
                            and not isinstance(fill_value.get("repeat"), bool)
                            and 0 <= fill_value["repeat"] <= 10000
                    )

                    if not (valid_string or valid_repeat_object):
                        raise ValueError(
                            f"{test_id}: Invalid value for fill."
                        )

                if action_type == "select":

                    if not isinstance(action.get("value"), str):
                        raise ValueError(
                            f"{test_id}: Invalid value for select."
                        )

                if action_type == "press":

                    key = action.get("key")

                    if not isinstance(key, str) or not key.strip():
                        raise ValueError(
                            f"{test_id}: Invalid key for press action."
                        )

                if action_type in {
                    "assert_text",
                    "assert_value",
                    "assert_attribute",
                    "assert_count"
                } and "expected" not in action:

                    raise ValueError(
                        f"{test_id}: Missing expected value for "
                        f"{action_type}."
                    )

                if action_type == "assert_attribute":

                    if not isinstance(action.get("attribute"), str):

                        raise ValueError(
                            f"{test_id}: Invalid attribute assertion."
                        )

                if action_type == "assert_count":

                    if (
                        not isinstance(action["expected"], int)
                        or isinstance(action["expected"], bool)
                        or action["expected"] < 0
                    ):

                        raise ValueError(
                            f"{test_id}: Invalid expected count."
                        )

            self.generated_plans.append({
                "test_case_id": test_id,
                "scenario_name": plan.get(
                    "scenario_name",
                    case.get("scenario_name", test_id)
                ),
                "plan_file": plan_file
            })

            print(
                f"[OK] Validated {test_id}: {len(actions)} actions"
            )

    # ==========================================
    # CREATE PROJECT FOLDERS
    # ==========================================

    def create_structure(self):

        for folder in [
            TESTS_DIR,
            PAGES_DIR,
            TEST_DATA_DIR,
            ARTIFACTS_DIR
        ]:

            folder.mkdir(
                parents=True,
                exist_ok=True
            )

        (TESTS_DIR / "__init__.py").write_text(
            "",
            encoding="utf-8"
        )

        (PAGES_DIR / "__init__.py").write_text(
            "",
            encoding="utf-8"
        )

    # ==========================================
    # COPY APPROVED ACTION PLANS
    # ==========================================

    def copy_action_plans(self):

        for item in self.generated_plans:

            source = item["plan_file"]

            destination = (
                TEST_DATA_DIR
                / source.name
            )

            shutil.copy2(
                source,
                destination
            )

            print(
                f"[OK] Copied {source.name}"
            )

    # ==========================================
    # CREATE GENERIC ACTION EXECUTOR
    # ==========================================

    def create_action_executor(self):

        content = r'''
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
'''

        output_file = (
            FRAMEWORK_DIR
            / "plan_executor.py"
        )

        output_file.write_text(
            content,
            encoding="utf-8"
        )

        print("[OK] Created plan_executor.py")

    # ==========================================
    # CREATE GENERIC PYTEST TEST FILE
    # ==========================================

    def create_test_file(self):

        content = r'''
import json
from pathlib import Path

import pytest

from plan_executor import ActionPlanExecutor


TEST_DATA_DIR = (
    Path(__file__).resolve().parents[1]
    / "test_data"
)


PLAN_FILES = sorted(
    TEST_DATA_DIR.glob("*_ai.json")
)


@pytest.mark.parametrize(
    "plan_file",
    PLAN_FILES,
    ids=lambda path: path.stem.replace("_ai", "")
)
def test_generated_action_plan(page, plan_file):

    with open(
        plan_file,
        "r",
        encoding="utf-8"
    ) as file:

        plan = json.load(file)

    print(
        f"\nRunning test case: {plan['test_case_id']}"
    )

    executor = ActionPlanExecutor(page)

    executor.execute_plan(plan)
'''

        output_file = (
            TESTS_DIR
            / "test_generated_action_plans.py"
        )

        output_file.write_text(
            content,
            encoding="utf-8"
        )

        print("[OK] Created generic pytest test file")

    # ==========================================
    # CREATE BROWSER FIXTURES
    # ==========================================

    def create_conftest(self):

        content = r'''
from pathlib import Path

import pytest

from playwright.sync_api import sync_playwright


ARTIFACTS_DIR = (
    Path(__file__).parent
    / "artifacts"
)


@pytest.fixture
def page(request):

    ARTIFACTS_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    with sync_playwright() as playwright:

        browser = playwright.chromium.launch(
            headless=True
        )

        context = browser.new_context()

        browser_page = context.new_page()

        yield browser_page

        report = getattr(
            request.node,
            "rep_call",
            None
        )

        if report and report.failed:

            screenshot_path = (
                ARTIFACTS_DIR
                / f"{request.node.name}.png"
            )

            browser_page.screenshot(
                path=str(screenshot_path),
                full_page=True
            )

            print(
                f"Failure screenshot: {screenshot_path}"
            )

        context.close()
        browser.close()


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):

    outcome = yield

    report = outcome.get_result()

    setattr(
        item,
        "rep_" + report.when,
        report
    )
'''

        (FRAMEWORK_DIR / "conftest.py").write_text(
            content,
            encoding="utf-8"
        )

        print("[OK] Created conftest.py")

    # ==========================================
    # CREATE CONFIGURATION
    # ==========================================

    def create_configuration(self):

        (FRAMEWORK_DIR / "pytest.ini").write_text(
            """[pytest]
testpaths = tests
python_files = test_*.py
python_functions = test_*
addopts = -v --tb=short --html=artifacts/report.html --self-contained-html
""",
            encoding="utf-8"
        )

        (FRAMEWORK_DIR / "requirements.txt").write_text(
            """playwright>=1.55.0
pytest>=8.0.0
pytest-html>=4.0.0
""",
            encoding="utf-8"
        )

        (FRAMEWORK_DIR / ".gitignore").write_text(
            """.venv/
__pycache__/
.pytest_cache/
artifacts/*
!.gitkeep
""",
            encoding="utf-8"
        )

        (ARTIFACTS_DIR / ".gitkeep").write_text(
            "",
            encoding="utf-8"
        )

        print("[OK] Created project configuration")

    # ==========================================
    # CREATE README
    # ==========================================

    def create_readme(self):

        content = """# Generic AI Action-Plan Playwright Framework

This standalone framework executes approved AI-generated
Playwright action plans using Python and pytest.

## Requirements

- Python 3.10+
- pip

## Setup

```powershell
python -m venv .venv
.venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
playwright install chromium
```

## Run tests

```powershell
python -m pytest
```

## Output

- HTML report: artifacts/report.html
- Failure screenshots: artifacts/

## Supported actions

- navigate
- fill
- click
- press
- select
- assert_visible
- assert_text
- assert_attribute
- assert_value
- assert_count

## Supported locator strategies

- id
- css
- xpath
- text
- placeholder
- role
- label

## Important

This project executes JSON action plans and does not require
Gemini or the original AI QA application at runtime.

Review test plans before running against sensitive systems.
Do not place passwords, API keys, or other secrets directly
inside action-plan JSON files.
"""

        (FRAMEWORK_DIR / "README.md").write_text(
            content,
            encoding="utf-8"
        )

    # ==========================================
    # CREATE MANIFEST
    # ==========================================

    def create_manifest(self):

        manifest = {
            "project_name": "Generic AI Action-Plan Playwright Framework",
            "generated_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "language": "Python",
            "framework": "Playwright",
            "test_runner": "pytest",
            "total_generated_tests": len(
                self.generated_plans
            ),
            "test_case_ids": [
                item["test_case_id"]
                for item in self.generated_plans
            ],
            "generated_test_file": (
                "tests/test_generated_action_plans.py"
            ),
            "execution_requires_gemini": False,
            "generation_status": "completed"
        }

        (FRAMEWORK_DIR / "framework_manifest.json").write_text(
            json.dumps(
                manifest,
                indent=4
            ),
            encoding="utf-8"
        )

    # ==========================================
    # CREATE ZIP
    # ==========================================

    def create_zip(self):

        ZIP_FILE.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        with zipfile.ZipFile(
            ZIP_FILE,
            "w",
            zipfile.ZIP_DEFLATED
        ) as archive:

            for file_path in FRAMEWORK_DIR.rglob("*"):

                if not file_path.is_file():
                    continue

                if any(
                    excluded in file_path.parts
                    for excluded in [
                        ".venv",
                        "__pycache__",
                        ".pytest_cache"
                    ]
                ):
                    continue

                if file_path.suffix == ".pyc":
                    continue

                archive.write(
                    file_path,
                    file_path.relative_to(
                        FRAMEWORK_DIR.parent
                    )
                )

        print(f"[OK] ZIP created: {ZIP_FILE}")

    # ==========================================
    # MAIN
    # ==========================================

    def run(self):

        print("\n========================================")
        print(" GENERIC ACTION-PLAN FRAMEWORK GENERATOR")
        print("========================================")

        self.load_approved_cases()

        self.load_action_plans()

        self.create_structure()

        self.copy_action_plans()

        self.create_action_executor()

        self.create_test_file()

        self.create_conftest()

        self.create_configuration()

        self.create_readme()

        self.create_manifest()

        self.create_zip()

        print("\n========================================")
        print(" FRAMEWORK GENERATION COMPLETED")
        print("========================================")

        print(
            f"Generated tests: {len(self.generated_plans)}"
        )

        print(
            f"Framework folder: {FRAMEWORK_DIR}"
        )

        print(
            f"ZIP package: {ZIP_FILE}"
        )


def main():

    generator = ActionPlanFrameworkGenerator()

    generator.run()


if __name__ == "__main__":

    main()
