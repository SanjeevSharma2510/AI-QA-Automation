
import json
import re
import zipfile

from datetime import datetime, timezone
from pathlib import Path


# =============================================================
# PROJECT PATHS
# =============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]

REVIEWED_CASES_FILE = (
    PROJECT_ROOT
    / "generated"
    / "test_cases"
    / "reviewed_test_cases.json"
)

FRAMEWORK_DIR = (
    PROJECT_ROOT
    / "generated"
    / "frameworks"
    / "python_playwright_project"
)

TESTS_DIR = FRAMEWORK_DIR / "tests"
PAGES_DIR = FRAMEWORK_DIR / "pages"
ARTIFACTS_DIR = FRAMEWORK_DIR / "artifacts"

ZIP_FILE = (
    PROJECT_ROOT
    / "generated"
    / "frameworks"
    / "python_playwright_project.zip"
)


class PythonPlaywrightProjectGenerator:

    def __init__(self):

        self.test_cases = []
        self.generated_test_files = []

    # =========================================================
    # LOAD AND VALIDATE APPROVED TEST CASES
    # =========================================================

    def load_approved_test_cases(self):

        print("\nLoading reviewed test cases...")

        if not REVIEWED_CASES_FILE.exists():

            raise FileNotFoundError(
                f"Reviewed test cases not found: "
                f"{REVIEWED_CASES_FILE}"
            )

        with open(
            REVIEWED_CASES_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            review_data = json.load(file)

        all_cases = review_data.get("test_cases", [])

        self.test_cases = [
            case for case in all_cases
            if (
                case.get("review_status") == "approved"
                and case.get("execution_status") == "passed"
            )
        ]

        if not self.test_cases:

            raise ValueError(
                "No eligible test cases found. "
                "Test cases must be both approved and passed."
            )

        print(
            f"[OK] Total reviewed cases: {len(all_cases)}"
        )

        print(
            f"[OK] Eligible approved cases: {len(self.test_cases)}"
        )

        for case in self.test_cases:

            print(
                f"[APPROVED] "
                f"{case['test_case_id']} - "
                f"{case['scenario_name']}"
            )

    # =========================================================
    # VALIDATE TEST CASE STRUCTURE
    # =========================================================

    def validate_test_cases(self):

        print("\nValidating approved test cases...")

        required_fields = [
            "test_case_id",
            "scenario_name",
            "scenario_type",
            "preconditions",
            "test_steps",
            "expected_results"
        ]

        seen_ids = set()

        for case in self.test_cases:

            for field in required_fields:

                if field not in case:

                    raise ValueError(
                        f"{case.get('test_case_id', 'Unknown')}: "
                        f"Missing field {field}"
                    )

            test_id = case["test_case_id"]

            if test_id in seen_ids:

                raise ValueError(
                    f"Duplicate test case ID: {test_id}"
                )

            seen_ids.add(test_id)

            if not isinstance(case["test_steps"], list):

                raise ValueError(
                    f"{test_id}: test_steps must be a list."
                )

            if not isinstance(case["preconditions"], list):

                raise ValueError(
                    f"{test_id}: preconditions must be a list."
                )

        print("[OK] Test case structure validated.")

    # =========================================================
    # EXTRACT APPLICATION URL
    # =========================================================

    def extract_base_url(self):

        for case in self.test_cases:

            for precondition in case.get("preconditions", []):

                urls = re.findall(
                    r"https?://[^\s'\"<>]+",
                    precondition
                )

                if urls:

                    return urls[0].rstrip(".,)")

        raise ValueError(
            "Could not find an application URL in "
            "the approved test case preconditions."
        )

    # =========================================================
    # EXTRACT PLACEHOLDER
    # =========================================================

    @staticmethod
    def extract_placeholder(case):

        combined_text = " ".join(
            case.get("test_steps", [])
            + case.get("expected_results", [])
        )

        match = re.search(
            r"placeholder(?:\s+text)?\s+(?:equals|is)\s+['\"]([^'\"]+)['\"]",
            combined_text,
            re.IGNORECASE
        )

        if match:

            return match.group(1)

        match = re.search(
            r"placeholder\s+['\"]([^'\"]+)['\"]",
            combined_text,
            re.IGNORECASE
        )

        if match:

            return match.group(1)

        # TodoMVC supported scenario default.
        return "What needs to be done?"

    # =========================================================
    # IDENTIFY SUPPORTED AUTOMATION SCENARIO
    # =========================================================

    def identify_scenario(self, case):

        scenario_name = case["scenario_name"].lower()

        test_id = case["test_case_id"]

        if (
            "initial rendering" in scenario_name
            or "input field" in scenario_name
            and "initial" in scenario_name
        ):

            return "initial_input_validation"

        if (
            "empty submission" in scenario_name
            or "empty todo" in scenario_name
        ):

            return "empty_submission"

        if (
            "boundary" in scenario_name
            or "string length" in scenario_name
            or "long string" in scenario_name
        ):

            return "boundary_input"

        raise ValueError(
            f"\nUnsupported automation scenario: "
            f"{test_id} - {case['scenario_name']}\n"
            "The generator currently supports:\n"
            "- Initial input validation\n"
            "- Empty submission validation\n"
            "- Boundary string input validation\n"
            "Add an automation mapping before generating "
            "this test case."
        )

    # =========================================================
    # CREATE PROJECT STRUCTURE
    # =========================================================

    def create_project_structure(self):

        print("\nCreating Python framework folders...")

        for folder in [
            TESTS_DIR,
            PAGES_DIR,
            ARTIFACTS_DIR
        ]:

            folder.mkdir(
                parents=True,
                exist_ok=True
            )

            print(
                f"[OK] {folder.relative_to(FRAMEWORK_DIR)}"
            )

        (TESTS_DIR / "__init__.py").write_text(
            "",
            encoding="utf-8"
        )

        (PAGES_DIR / "__init__.py").write_text(
            "",
            encoding="utf-8"
        )

    # =========================================================
    # CREATE PAGE OBJECT
    # =========================================================

    def create_page_object(self):

        placeholder = self.extract_placeholder(
            self.test_cases[0]
        )

        content = f'''from playwright.sync_api import Page, Locator


class TodoPage:

    def __init__(self, page: Page):

        self.page = page

        self.todo_input: Locator = page.get_by_placeholder(
            {placeholder!r}
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
'''

        output_file = PAGES_DIR / "todo_page.py"

        output_file.write_text(
            content,
            encoding="utf-8"
        )

        print("[OK] Created pages/todo_page.py")

    # =========================================================
    # GENERATE PYTEST TEST FILES
    # =========================================================

    def generate_test_file(self, case):

        scenario = self.identify_scenario(case)

        test_id = case["test_case_id"]

        safe_test_id = re.sub(
            r"[^A-Za-z0-9_]",
            "_",
            test_id
        )

        placeholder = self.extract_placeholder(case)

        test_function = f"test_{safe_test_id.lower()}"

        if scenario == "initial_input_validation":

            test_body = f'''
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

    assert input_field.get_attribute("placeholder") == {placeholder!r}, (
        "Incorrect placeholder text."
    )

    assert input_field.input_value() == "", (
        "Input field should initially be empty."
    )
'''

        elif scenario == "empty_submission":

            test_body = '''
    todo_page.navigate(base_url)

    initial_count = todo_page.get_todo_count()

    todo_page.todo_input.fill("")

    todo_page.todo_input.press("Enter")

    final_count = todo_page.get_todo_count()

    assert final_count == initial_count, (
        "An empty todo item was created."
    )
'''

        elif scenario == "boundary_input":

            test_body = '''
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
'''

        else:

            raise ValueError(
                f"Missing automation mapping for {test_id}"
            )

        content = f'''import pytest

from pages.todo_page import TodoPage


@pytest.mark.{scenario}
@pytest.mark.test_case_id("{test_id}")
def {test_function}(page, base_url):

    todo_page = TodoPage(page)
{test_body}
'''

        output_file = TESTS_DIR / f"{safe_test_id.lower()}_test.py"

        output_file.write_text(
            content,
            encoding="utf-8"
        )

        self.generated_test_files.append(
            output_file.name
        )

        print(
            f"[OK] Generated {output_file.name}"
        )

    def generate_all_tests(self):

        print("\nGenerating approved Playwright tests...")

        for case in self.test_cases:

            self.generate_test_file(case)

    # =========================================================
    # CREATE PYTEST FIXTURES
    # =========================================================

    def create_conftest(self):

        content = '''import os
from pathlib import Path

import pytest

from playwright.sync_api import sync_playwright


ARTIFACTS_DIR = Path(__file__).parent / "artifacts"


@pytest.fixture(scope="session")
def base_url():

    return os.getenv(
        "BASE_URL",
        "https://demo.playwright.dev/todomvc/#/"
    )


@pytest.fixture
def page(request):

    ARTIFACTS_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    with sync_playwright() as playwright:

        browser = playwright.chromium.launch(
            headless=os.getenv("HEADLESS", "true").lower() == "true"
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

            test_name = request.node.name

            screenshot_path = (
                ARTIFACTS_DIR
                / f"{test_name}.png"
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

        # Ensure screenshots are captured using the call report.
        content = content.replace(
            'request.node,\n            "rep_call",',
            'request.node,\n            "rep_call",'
        )

        output_file = FRAMEWORK_DIR / "conftest.py"

        output_file.write_text(
            content,
            encoding="utf-8"
        )

        print("[OK] Created conftest.py")

    # =========================================================
    # CREATE PYTEST CONFIGURATION
    # =========================================================

    def create_pytest_config(self):

        content = '''[pytest]

testpaths = tests

python_files = *_test.py

python_functions = test_*

addopts = -v --tb=short --html=artifacts/report.html --self-contained-html

markers =
    initial_input_validation: Initial input field validation
    empty_submission: Empty submission validation
    boundary_input: Boundary input validation
    test_case_id(id): Original AI-generated test case ID
'''

        output_file = FRAMEWORK_DIR / "pytest.ini"

        output_file.write_text(
            content,
            encoding="utf-8"
        )

        print("[OK] Created pytest.ini")

    # =========================================================
    # CREATE REQUIREMENTS
    # =========================================================

    def create_requirements(self):

        content = '''playwright>=1.55.0
pytest>=8.0.0
pytest-html>=4.0.0
'''

        output_file = FRAMEWORK_DIR / "requirements.txt"

        output_file.write_text(
            content,
            encoding="utf-8"
        )

        print("[OK] Created requirements.txt")

    # =========================================================
    # CREATE ENVIRONMENT FILE
    # =========================================================

    def create_environment_files(self):

        env_example = '''# Application URL
BASE_URL=https://demo.playwright.dev/todomvc/#/

# true = headless browser
# false = visible browser
HEADLESS=true
'''

        (FRAMEWORK_DIR / ".env.example").write_text(
            env_example,
            encoding="utf-8"
        )

        # No secrets or real credentials are generated.
        (FRAMEWORK_DIR / ".gitignore").write_text(
            """.env
.venv/
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

        print("[OK] Created environment files")

    # =========================================================
    # CREATE README
    # =========================================================

    def create_readme(self):

        content = '''# AI Generated Python Playwright Framework

This framework contains Python Playwright tests generated
from human-approved and successfully executed test cases.

## Requirements

- Python 3.10+
- pip

## 1. Create virtual environment

Windows:

```powershell
python -m venv .venv
.venv\\Scripts\\Activate.ps1
```

Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## 2. Install dependencies

```bash
pip install -r requirements.txt
```

## 3. Install Chromium

```bash
playwright install chromium
```

## 4. Configure application URL

Copy `.env.example` to `.env`.

Update BASE_URL with your application URL.

Set HEADLESS=false to see the browser.

Note: Environment variables must be loaded by your shell
or your chosen environment loader before running pytest.

Windows PowerShell example:

```powershell
$env:BASE_URL="https://demo.playwright.dev/todomvc/#/"
$env:HEADLESS="false"
```

## 5. Run all tests

```bash
pytest
```

## 6. Run tests with visible browser

PowerShell:

```powershell
$env:HEADLESS="false"
pytest
```

## 7. HTML report

After execution, open:

```text
artifacts/report.html
```

## 8. Failure screenshots

Screenshots are saved under:

```text
artifacts/
```

## Project structure

- tests/: Generated pytest test scripts
- pages/: Page Object Model classes
- conftest.py: Browser fixtures
- pytest.ini: Pytest configuration
- requirements.txt: Dependencies
- artifacts/: Reports and failure screenshots

## Important

The generated framework does not require Gemini to execute.

Only human-approved test cases with passed execution
are included in this framework.

Review the generated test scripts before running them
against production or other sensitive environments.
'''

        output_file = FRAMEWORK_DIR / "README.md"

        output_file.write_text(
            content,
            encoding="utf-8"
        )

        print("[OK] Created README.md")

    # =========================================================
    # CREATE MANIFEST
    # =========================================================

    def create_manifest(self):

        manifest = {
            "project_name": "AI Generated Python Playwright Framework",
            "generated_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "framework": "Playwright",
            "language": "Python",
            "test_runner": "pytest",
            "source_file": str(
                REVIEWED_CASES_FILE.relative_to(PROJECT_ROOT)
            ),
            "total_generated_tests": len(self.test_cases),
            "test_case_ids": [
                case["test_case_id"]
                for case in self.test_cases
            ],
            "generated_test_files": self.generated_test_files,
            "ai_required_for_execution": False,
            "generation_status": "completed"
        }

        output_file = FRAMEWORK_DIR / "framework_manifest.json"

        output_file.write_text(
            json.dumps(
                manifest,
                indent=4
            ),
            encoding="utf-8"
        )

        print("[OK] Created framework_manifest.json")

    # =========================================================
    # CREATE ZIP PACKAGE
    # =========================================================

    def create_zip_package(self):

        print("\nCreating downloadable ZIP package...")

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

                if file_path.name.endswith(".pyc"):

                    continue

                archive.write(
                    file_path,
                    file_path.relative_to(
                        FRAMEWORK_DIR.parent
                    )
                )

        print(f"[OK] ZIP created: {ZIP_FILE}")

    # =========================================================
    # MAIN GENERATION
    # =========================================================

    def run(self):

        print("\n========================================")
        print(" PYTHON PLAYWRIGHT PROJECT GENERATOR")
        print("========================================")

        self.load_approved_test_cases()

        self.validate_test_cases()

        # Validate all scenarios before writing the project.
        # Unsupported cases stop generation.
        for case in self.test_cases:

            self.identify_scenario(case)

        self.create_project_structure()

        self.create_page_object()

        self.generate_all_tests()

        self.create_conftest()

        self.create_pytest_config()

        self.create_requirements()

        self.create_environment_files()

        self.create_readme()

        self.create_manifest()

        self.create_zip_package()

        print("\n========================================")
        print(" FRAMEWORK GENERATION COMPLETED")
        print("========================================")

        print(
            f"Generated tests: {len(self.test_cases)}"
        )

        print(
            f"Framework folder: {FRAMEWORK_DIR}"
        )

        print(
            f"ZIP package: {ZIP_FILE}"
        )


# =============================================================
# APPLICATION ENTRY POINT
# =============================================================

def main():

    try:

        generator = PythonPlaywrightProjectGenerator()

        generator.run()

    except Exception as error:

        print("\nFramework generation failed.")

        print(f"Reason: {error}")

        raise


if __name__ == "__main__":

    main()
