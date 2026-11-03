
import json
import re
from pathlib import Path
from datetime import datetime, timezone


PROJECT_ROOT = Path(__file__).resolve().parents[3]

INPUT_FILE = (
    PROJECT_ROOT
    / "generated"
    / "test_cases"
    / "reviewed_test_cases.json"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "generated"
    / "frameworks"
    / "playwright_project"
)

TESTS_DIR = OUTPUT_DIR / "tests"


class PlaywrightScriptGenerator:

    def __init__(self):
        TESTS_DIR.mkdir(parents=True, exist_ok=True)

    def load_approved_test_cases(self):
        print("\nLoading reviewed test cases...", flush=True)

        if not INPUT_FILE.exists():
            raise FileNotFoundError(
                f"Input file not found: {INPUT_FILE}"
            )

        with open(INPUT_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        if isinstance(data, dict):
            test_cases = data.get("test_cases", [])
        elif isinstance(data, list):
            test_cases = data
        else:
            raise ValueError("Unexpected JSON structure.")

        approved = [
            case for case in test_cases
            if case.get("review_status") == "approved"
        ]

        print(f"Total test cases: {len(test_cases)}")
        print(f"Approved test cases: {len(approved)}")

        return approved

    @staticmethod
    def extract_url(preconditions):

        for condition in preconditions:
            match = re.search(
                r"https?://[^\s'\"<>]+",
                condition
            )

            if match:
                return match.group(0).rstrip(".,)")

        raise ValueError("Website URL not found in preconditions.")

    @staticmethod
    def extract_placeholder(test_steps):

        for step in test_steps:
            match = re.search(
                r"placeholder text equals ['\"](.+?)['\"]",
                step,
                re.IGNORECASE
            )

            if match:
                return match.group(1)

        raise ValueError("Expected placeholder not found in test steps.")

    def generate_input_validation_script(self, test_case):

        scenario_name = test_case["scenario_name"]

        url = self.extract_url(
            test_case.get("preconditions", [])
        )

        placeholder = self.extract_placeholder(
            test_case.get("test_steps", [])
        )

        js_url = json.dumps(url)
        js_placeholder = json.dumps(placeholder)
        js_title = json.dumps(scenario_name)

        script = f'''import {{ test, expect }} from "@playwright/test";

test({js_title}, async ({{ page }}) => {{

    // Open the application.
    await page.goto({js_url});

    // Locate the TodoMVC input field.
    const todoInput = page.getByPlaceholder(
        {js_placeholder},
        {{ exact: true }}
    );

    // Verify that the input field is visible.
    await expect(todoInput).toBeVisible();

    // Verify its placeholder.
    await expect(todoInput).toHaveAttribute(
        "placeholder",
        {js_placeholder}
    );

    // Verify that the input is enabled.
    await expect(todoInput).toBeEnabled();

    // Verify that the input is not readonly.
    await expect(todoInput).not.toHaveAttribute("readonly");

    // Verify that the input is initially empty.
    await expect(todoInput).toHaveValue("");

}});
'''

        return script

    def generate_script(self, test_case):

        scenario_type = test_case.get(
            "scenario_type", ""
        ).lower()

        steps = " ".join(
            test_case.get("test_steps", [])
        ).lower()

        is_input_validation = (
            scenario_type == "ui_validation"
            and "input field" in steps
            and "placeholder" in steps
            and "readonly" in steps
        )

        if is_input_validation:
            return self.generate_input_validation_script(
                test_case
            )

        raise NotImplementedError(
            f"Unsupported test case: "
            f"{test_case.get('test_case_id')}"
        )

    def run(self):

        print("\n======================================")
        print(" PLAYWRIGHT SCRIPT GENERATOR")
        print("======================================")

        approved_cases = self.load_approved_test_cases()

        if not approved_cases:
            print("No approved test cases found.")
            return

        generated_count = 0
        failures = []

        for test_case in approved_cases:

            test_case_id = test_case.get(
                "test_case_id", "UNKNOWN"
            )

            try:
                script = self.generate_script(test_case)

                output_file = (
                    TESTS_DIR / f"{test_case_id}.spec.js"
                )

                output_file.write_text(
                    script,
                    encoding="utf-8"
                )

                generated_count += 1

                print(f"\nGenerated successfully: {output_file}")

            except Exception as error:
                failures.append({
                    "test_case_id": test_case_id,
                    "error": str(error)
                })

                print(f"\nGeneration failed: {test_case_id}")
                print(f"Reason: {error}")

        summary = {
            "generated_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "total_approved": len(approved_cases),
            "generated_count": generated_count,
            "failed_count": len(failures),
            "failures": failures
        }

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        summary_file = OUTPUT_DIR / "generation_summary.json"

        summary_file.write_text(
            json.dumps(summary, indent=4),
            encoding="utf-8"
        )

        print("\n========== GENERATION SUMMARY ==========")
        print(f"Approved cases: {len(approved_cases)}")
        print(f"Generated scripts: {generated_count}")
        print(f"Failed scripts: {len(failures)}")
        print(f"Summary file: {summary_file}")


if __name__ == "__main__":
    generator = PlaywrightScriptGenerator()
    generator.run()
