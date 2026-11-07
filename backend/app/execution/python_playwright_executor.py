
import asyncio
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from playwright.async_api import async_playwright


PROJECT_ROOT = Path(__file__).resolve().parents[3]

TEST_CASES_FILE = (
    PROJECT_ROOT / "generated" / "test_cases" / "test_cases.json"
)

RESULTS_DIR = PROJECT_ROOT / "generated" / "execution"

SCREENSHOTS_DIR = RESULTS_DIR / "screenshots"

RESULTS_FILE = RESULTS_DIR / "execution_results.json"


class PythonPlaywrightExecutor:

    def __init__(self):

        SCREENSHOTS_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        self.results = []

    def load_test_cases(self):

        if not TEST_CASES_FILE.exists():
            raise FileNotFoundError(
                f"Test cases file not found: {TEST_CASES_FILE}"
            )

        with open(TEST_CASES_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        test_cases = data.get("test_cases", [])

        if not test_cases:
            raise ValueError("No test cases found.")

        return test_cases

    def extract_url(self, test_case):

        for precondition in test_case.get("preconditions", []):

            match = re.search(
                r"https?://[^\s]+",
                precondition
            )

            if match:
                return match.group(0).rstrip(".,)")

        return None

    def extract_placeholder(self, test_case):

        combined_text = " ".join(
            test_case.get("test_steps", [])
        )

        match = re.search(
            r"placeholder\s*(?:text\s*)?(?:equals|=)\s*['\"](.+?)['\"]",
            combined_text,
            re.IGNORECASE
        )

        if match:
            return match.group(1)

        match = re.search(
            r"placeholder=['\"](.+?)['\"]",
            combined_text,
            re.IGNORECASE
        )

        if match:
            return match.group(1)

        return None

    async def run_ui_validation(self, page, test_case, placeholder):

        input_field = page.get_by_placeholder(
            placeholder,
            exact=True
        )

        await input_field.wait_for(
            state="visible",
            timeout=10000
        )

        assert await input_field.is_visible(), (
            "Input field is not visible."
        )

        assert await input_field.is_enabled(), (
            "Input field is disabled."
        )

        is_readonly = await input_field.get_attribute("readonly")

        assert is_readonly is None, (
            "Input field is readonly."
        )

        actual_placeholder = await input_field.get_attribute(
            "placeholder"
        )

        assert actual_placeholder == placeholder, (
            f"Expected placeholder '{placeholder}', "
            f"but found '{actual_placeholder}'."
        )

        actual_value = await input_field.input_value()

        assert actual_value == "", (
            f"Expected an empty input, but found '{actual_value}'."
        )

        return {
            "checks": [
                "Input is visible",
                "Input is enabled",
                "Input is editable",
                "Placeholder matches",
                "Input is empty"
            ]
        }

    async def run_empty_submission(self, page, test_case, placeholder):

        input_field = page.get_by_placeholder(
            placeholder,
            exact=True
        )

        await input_field.wait_for(
            state="visible",
            timeout=10000
        )

        await input_field.fill("")

        before_count = await page.locator(
            ".todo-list li"
        ).count()

        await input_field.press("Enter")

        await page.wait_for_timeout(500)

        after_count = await page.locator(
            ".todo-list li"
        ).count()

        assert after_count == before_count, (
            "An empty todo item was created after pressing Enter."
        )

        return {
            "checks": [
                "Input was empty before submission",
                "Enter key was pressed",
                "No empty todo item was created"
            ],
            "todo_count_before": before_count,
            "todo_count_after": after_count
        }

    async def run_boundary_input(self, page, test_case, placeholder):

        input_field = page.get_by_placeholder(
            placeholder,
            exact=True
        )

        await input_field.wait_for(
            state="visible",
            timeout=10000
        )

        test_values = [
            "A",
            "B" * 255,
            "C" * 1000
        ]

        created_items = []

        for value in test_values:

            await input_field.fill(value)

            await input_field.press("Enter")

            item = page.locator(
                ".todo-list li"
            ).filter(
                has_text=value
            )

            await item.first.wait_for(
                state="visible",
                timeout=10000
            )

            item_text = (
                await item.first.locator("label").inner_text()
            )

            assert item_text == value, (
                f"Todo text did not match. "
                f"Expected length: {len(value)}, "
                f"Actual length: {len(item_text)}"
            )

            created_items.append({
                "text_length": len(value),
                "displayed_correctly": True
            })

        assert await input_field.input_value() == "", (
            "Input was not cleared after adding todos."
        )

        return {
            "checks": [
                "Single-character todo created",
                "255-character todo created",
                "1000-character todo created",
                "Input cleared after submission"
            ],
            "created_items": created_items
        }

    async def execute_one(self, browser, test_case):

        test_case_id = test_case.get(
            "test_case_id",
            "UNKNOWN"
        )

        started_at = datetime.now(timezone.utc)

        result = {
            "test_case_id": test_case_id,
            "scenario_name": test_case.get("scenario_name"),
            "execution_status": "blocked",
            "started_at": started_at.isoformat(),
            "finished_at": None,
            "duration_seconds": None,
            "checks": [],
            "error": None,
            "screenshot": None
        }

        page = None

        try:

            url = self.extract_url(test_case)

            if not url:
                raise ValueError(
                    "No application URL found in test case preconditions."
                )

            placeholder = self.extract_placeholder(test_case)

            if not placeholder:
                raise ValueError(
                    "Could not identify the input placeholder."
                )

            context = await browser.new_context(
                viewport={
                    "width": 1366,
                    "height": 768
                }
            )

            page = await context.new_page()

            print(f"\nExecuting {test_case_id}")
            print(f"Opening: {url}")

            await page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=60000
            )

            scenario_type = test_case.get(
                "scenario_type",
                ""
            ).lower()

            scenario_name = test_case.get(
                "scenario_name",
                ""
            ).lower()

            if (
                scenario_type == "ui_validation"
                and "initial rendering" in scenario_name
            ):

                details = await self.run_ui_validation(
                    page,
                    test_case,
                    placeholder
                )

            elif (
                scenario_type == "negative"
                and "empty submission" in scenario_name
            ):

                details = await self.run_empty_submission(
                    page,
                    test_case,
                    placeholder
                )

            elif (
                scenario_type == "boundary"
                and "boundary string length" in scenario_name
            ):

                details = await self.run_boundary_input(
                    page,
                    test_case,
                    placeholder
                )

            else:

                raise NotImplementedError(
                    "This test scenario does not have an execution handler yet."
                )

            result["execution_status"] = "passed"
            result["checks"] = details

        except NotImplementedError as error:

            result["execution_status"] = "blocked"
            result["error"] = str(error)

        except Exception as error:

            result["execution_status"] = "failed"
            result["error"] = str(error)

        finally:

            if page:

                screenshot_path = (
                    SCREENSHOTS_DIR / f"{test_case_id}.png"
                )

                try:

                    await page.screenshot(
                        path=str(screenshot_path),
                        full_page=True
                    )

                    result["screenshot"] = str(
                        screenshot_path.relative_to(PROJECT_ROOT)
                    )

                except Exception as screenshot_error:

                    result["screenshot_error"] = str(
                        screenshot_error
                    )

                await page.context.close()

        finished_at = datetime.now(timezone.utc)

        result["finished_at"] = finished_at.isoformat()

        result["duration_seconds"] = round(
            (finished_at - started_at).total_seconds(),
            2
        )

        print(
            f"{test_case_id}: "
            f"{result['execution_status'].upper()}"
        )

        return result

    def save_results(self):

        report = {
            "execution_started": (
                self.results[0]["started_at"]
                if self.results else None
            ),
            "execution_completed": datetime.now(
                timezone.utc
            ).isoformat(),
            "total": len(self.results),
            "passed": sum(
                item["execution_status"] == "passed"
                for item in self.results
            ),
            "failed": sum(
                item["execution_status"] == "failed"
                for item in self.results
            ),
            "blocked": sum(
                item["execution_status"] == "blocked"
                for item in self.results
            ),
            "results": self.results
        }

        with open(
            RESULTS_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                report,
                file,
                indent=4,
                ensure_ascii=False
            )

        print(f"\nExecution report saved: {RESULTS_FILE}")

    async def run_all(self):

        test_cases = self.load_test_cases()

        print("\n======================================")
        print("PYTHON PLAYWRIGHT VISUAL EXECUTION")
        print("======================================")

        print(f"Total test cases: {len(test_cases)}")

        async with async_playwright() as playwright:

            browser = await playwright.chromium.launch(
                headless=False
            )

            try:

                for test_case in test_cases:

                    result = await self.execute_one(
                        browser,
                        test_case
                    )

                    self.results.append(result)

            finally:

                await browser.close()

        self.save_results()

        print("\n========== EXECUTION SUMMARY ==========")

        print(f"Total:   {len(self.results)}")

        print(
            "Passed:  ",
            sum(
                item["execution_status"] == "passed"
                for item in self.results
            )
        )

        print(
            "Failed:  ",
            sum(
                item["execution_status"] == "failed"
                for item in self.results
            )
        )

        print(
            "Blocked: ",
            sum(
                item["execution_status"] == "blocked"
                for item in self.results
            )
        )

        print("=======================================")


async def main():

    executor = PythonPlaywrightExecutor()

    await executor.run_all()


if __name__ == "__main__":

    asyncio.run(main())
