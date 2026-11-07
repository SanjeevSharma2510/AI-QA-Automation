
import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

from backend.app.ai.gemini_client import GeminiClient


class TestCaseReviewAgent:

    EDITABLE_FIELDS = [
        "module",
        "scenario_name",
        "scenario_type",
        "priority",
        "preconditions",
        "test_steps",
        "expected_results",
        "source_workflow_ids",
        "evidence"
    ]

    VALID_TYPES = [
        "positive",
        "negative",
        "boundary",
        "ui_validation"
    ]

    VALID_PRIORITIES = ["high", "medium", "low"]

    def __init__(self):

        self.project_root = Path(__file__).resolve().parents[3]

        self.input_file = (
            self.project_root
            / "generated"
            / "test_cases"
            / "test_cases.json"
        )

        self.output_folder = (
            self.project_root
            / "generated"
            / "test_cases"
        )

        self.review_file = (
            self.output_folder
            / "reviewed_test_cases.json"
        )

        self.approved_excel = (
            self.output_folder
            / "approved_test_cases.xlsx"
        )

        # Latest visual execution report
        self.execution_results_file = (
            self.project_root
            / "generated"
            / "execution"
            / "execution_results.json"
        )

        self.test_cases = []
        self.review_data = None

        # Gemini is initialized only when AI improvement is requested.
        self.gemini = None

    # =========================================================
    # ATTACH EXECUTION RESULTS
    # =========================================================

    def attach_execution_results(self):
        """Attach the latest execution result to each test case."""

        execution_results = {}

        if self.execution_results_file.exists():

            with open(
                self.execution_results_file,
                "r",
                encoding="utf-8"
            ) as file:

                report = json.load(file)

            execution_results = {
                result["test_case_id"]: result
                for result in report.get("results", [])
                if result.get("test_case_id")
            }

        for case in self.test_cases:

            test_id = case["test_case_id"]

            result = execution_results.get(test_id)

            if not result:

                case["execution_status"] = "not_executed"
                case["execution_result"] = None

                if case.get("review_status") == "approved":
                    case["review_status"] = "pending"

                continue

            # An edit made after execution invalidates old evidence.
            updated_at = case.get("updated_at")
            finished_at = result.get("finished_at")

            if updated_at and finished_at:

                try:

                    updated_time = datetime.fromisoformat(
                        updated_at
                    )

                    finished_time = datetime.fromisoformat(
                        finished_at
                    )

                    if updated_time > finished_time:

                        case["execution_status"] = "not_executed"
                        case["execution_result"] = None
                        case["review_status"] = "pending"

                        continue

                except ValueError:
                    pass

            case["execution_status"] = result.get(
                "execution_status",
                "not_executed"
            )

            case["execution_result"] = result

            # A failed or blocked execution cannot retain approval.
            if (
                case["execution_status"] != "passed"
                and case.get("review_status") == "approved"
            ):

                case["review_status"] = "pending"

        print("\nExecution results attached to test cases.")

    # =========================================================
    # LOAD TEST CASES
    # =========================================================

    def load_test_cases(self):
        """Load generated test cases or resume an existing review."""

        if self.review_file.exists():

            print("\nExisting review found.")

            choice = input(
                "Resume existing review? (Y/N): "
            ).strip().lower()

            if choice == "y":

                with open(
                    self.review_file,
                    "r",
                    encoding="utf-8"
                ) as file:

                    self.review_data = json.load(file)

                self.test_cases = self.review_data["test_cases"]

                self.attach_execution_results()

                self.validate_all_cases()

                self.save_review()

                print("Existing review loaded successfully.")

                return

        if not self.input_file.exists():

            raise FileNotFoundError(
                "test_cases.json not found. "
                "Run the test case generator first."
            )

        with open(
            self.input_file,
            "r",
            encoding="utf-8"
        ) as file:

            generated_data = json.load(file)

        self.test_cases = deepcopy(
            generated_data.get("test_cases", [])
        )

        if not self.test_cases:

            raise ValueError("No generated test cases found.")

        # Attach the latest execution evidence.
        self.attach_execution_results()

        self.validate_all_cases()

        for case in self.test_cases:

            case["review_status"] = "pending"

        self.review_data = {
            "review_id": datetime.now().strftime(
                "%Y%m%d_%H%M%S"
            ),
            "created_at": datetime.now().isoformat(),
            "source_file": "test_cases.json",
            "test_cases": self.test_cases,
            "review_summary": {}
        }

        self.save_review()

        print(
            f"\nLoaded {len(self.test_cases)} test cases."
        )

    # =========================================================
    # VALIDATE TEST CASES
    # =========================================================

    def validate_all_cases(self):
        """Validate the structure of all test cases."""

        if not isinstance(self.test_cases, list):

            raise ValueError("Test cases must be a list.")

        required_fields = [
            "test_case_id",
            "module",
            "scenario_name",
            "scenario_type",
            "priority",
            "preconditions",
            "test_steps",
            "expected_results",
            "source_workflow_ids",
            "evidence"
        ]

        seen_ids = set()

        for case in self.test_cases:

            if not isinstance(case, dict):

                raise ValueError("Invalid test case object.")

            for field in required_fields:

                if field not in case:

                    raise ValueError(
                        f"{case.get('test_case_id', 'Unknown')}: "
                        f"Missing {field}"
                    )

            test_id = case["test_case_id"]

            if not isinstance(test_id, str) or not test_id.strip():

                raise ValueError("Invalid test case ID.")

            if test_id in seen_ids:

                raise ValueError(
                    f"Duplicate test case ID: {test_id}"
                )

            seen_ids.add(test_id)

            if case["scenario_type"] not in self.VALID_TYPES:

                raise ValueError(
                    f"{test_id}: Invalid scenario type."
                )

            if case["priority"] not in self.VALID_PRIORITIES:

                raise ValueError(
                    f"{test_id}: Invalid priority."
                )

            for field in [
                "preconditions",
                "test_steps",
                "expected_results",
                "source_workflow_ids",
                "evidence"
            ]:

                value = case[field]

                if (
                    not isinstance(value, list)
                    or not value
                    or not all(
                        isinstance(item, str) and item.strip()
                        for item in value
                    )
                ):

                    raise ValueError(
                        f"{test_id}: Invalid {field}."
                    )

    # =========================================================
    # DISPLAY TEST CASE
    # =========================================================

    def display_test_case(self, case):

        print("\n" + "=" * 60)

        print(f"ID: {case['test_case_id']}")
        print(f"Module: {case['module']}")
        print(f"Scenario: {case['scenario_name']}")
        print(f"Type: {case['scenario_type']}")
        print(f"Priority: {case['priority']}")

        print(
            f"Review Status: "
            f"{case.get('review_status', 'pending')}"
        )

        print(
            f"Execution Status: "
            f"{case.get('execution_status', 'not_executed')}"
        )

        execution_result = case.get("execution_result")

        if execution_result:

            print("\nExecution Details:")

            print(
                f"Duration: "
                f"{execution_result.get('duration_seconds', 'N/A')} seconds"
            )

            print(
                f"Error: "
                f"{execution_result.get('error') or 'None'}"
            )

            checks = execution_result.get("checks", {})

            if isinstance(checks, dict):

                for check in checks.get("checks", []):

                    print(f"- {check}")

            screenshot = execution_result.get("screenshot")

            if screenshot:

                print(f"Screenshot: {screenshot}")

        print("\nPreconditions:")

        for item in case["preconditions"]:

            print(f"- {item}")

        print("\nTest Steps:")

        for index, step in enumerate(case["test_steps"], 1):

            print(f"{index}. {step}")

        print("\nExpected Results:")

        for item in case["expected_results"]:

            print(f"- {item}")

        print("\nSource Workflows:")

        for item in case["source_workflow_ids"]:

            print(f"- {item}")

        print("=" * 60)

    # =========================================================
    # EDIT TEST CASE
    # =========================================================

    def edit_list_field(self, field, current_values):

        print(f"\nCurrent {field}:")

        for index, value in enumerate(current_values, 1):

            print(f"{index}. {value}")

        print(
            "\nEnter replacement values one per line. "
            "Type DONE when finished."
        )

        updated_values = []

        while True:

            value = input("> ").strip()

            if value.upper() == "DONE":

                break

            if value:

                updated_values.append(value)

        if not updated_values:

            print("Empty values are not allowed.")

            return current_values

        return updated_values

    def edit_test_case(self, case):

        print("\n========== EDIT TEST CASE ==========")

        while True:

            for index, field in enumerate(
                self.EDITABLE_FIELDS,
                1
            ):

                print(f"{index}. {field}")

            print("0. Finish editing")

            choice = input("\nSelect field: ").strip()

            if choice == "0":

                break

            try:

                field = self.EDITABLE_FIELDS[
                    int(choice) - 1
                ]

            except (ValueError, IndexError):

                print("Invalid selection.")

                continue

            current_value = case[field]

            if isinstance(current_value, list):

                case[field] = self.edit_list_field(
                    field,
                    current_value
                )

            else:

                print(f"Current value: {current_value}")

                new_value = input(
                    "Enter new value: "
                ).strip()

                if new_value:

                    case[field] = new_value

            print(f"{field} updated.")

        # Revalidate after editing.
        self.validate_all_cases()

        # Editing invalidates previous execution evidence.
        case["review_status"] = "pending"
        case["execution_status"] = "not_executed"
        case["execution_result"] = None
        case["updated_at"] = datetime.now().isoformat()

        print(
            "Test case updated. "
            "Execution must be performed again before approval."
        )

    # =========================================================
    # GEMINI IMPROVEMENT
    # =========================================================

    def get_gemini(self):

        if self.gemini is None:

            self.gemini = GeminiClient()

        return self.gemini

    def improve_with_ai(self, case):
        """Improve one test case using Gemini."""

        print("\nAsking Gemini to improve this test case...")

        prompt = f"""
You are an expert QA test engineer.

Improve the following test case.

Make the steps clear, specific and executable.
Improve expected results.
Do not invent business rules.
Do not change its test case ID.
Do not invent application functionality.
Preserve source workflow references and evidence.

CURRENT TEST CASE:

{json.dumps(case, indent=2, ensure_ascii=False)}

Return ONLY valid JSON using the same test case structure.
Do not include review_status or updated_at.
"""

        response = self.get_gemini().generate_json(prompt)

        improved_case = json.loads(response)

        improved_case["test_case_id"] = case["test_case_id"]

        for field in self.EDITABLE_FIELDS:

            if field not in improved_case:

                raise ValueError(
                    f"AI improvement missing field: {field}"
                )

        # Validate the candidate before replacing the original.
        previous_cases = self.test_cases

        try:

            self.test_cases = [improved_case]

            self.validate_all_cases()

        except Exception:

            self.test_cases = previous_cases

            raise

        self.test_cases = previous_cases

        case.clear()
        case.update(improved_case)

        case["review_status"] = "pending"
        case["execution_status"] = "not_executed"
        case["execution_result"] = None
        case["updated_at"] = datetime.now().isoformat()

        print(
            "AI improvement applied. "
            "Please execute and review this test case again."
        )

    # =========================================================
    # ADD MANUAL TEST CASE
    # =========================================================

    def add_manual_test_case(self):

        print("\n========== ADD NEW TEST CASE ==========")

        test_id = input("Test case ID: ").strip()

        if any(
            case["test_case_id"] == test_id
            for case in self.test_cases
        ):

            print("This test case ID already exists.")

            return

        case = {
            "test_case_id": test_id,
            "module": input("Module: ").strip(),
            "scenario_name": input("Scenario name: ").strip(),
            "scenario_type": input(
                "Type (positive/negative/boundary/ui_validation): "
            ).strip().lower(),
            "priority": input(
                "Priority (high/medium/low): "
            ).strip().lower(),
            "preconditions": [],
            "test_steps": [],
            "expected_results": [],
            "source_workflow_ids": [],
            "evidence": [],
            "review_status": "pending",
            "created_by": "user",
            "execution_status": "not_executed",
            "execution_result": None
        }

        for field in [
            "preconditions",
            "test_steps",
            "expected_results",
            "source_workflow_ids",
            "evidence"
        ]:

            print(
                f"\nEnter {field}, one per line. DONE to finish."
            )

            case[field] = []

            while True:

                value = input("> ").strip()

                if value.upper() == "DONE":

                    break

                if value:

                    case[field].append(value)

        self.test_cases.append(case)

        try:

            self.validate_all_cases()

        except Exception as error:

            self.test_cases.pop()

            print(f"Invalid test case: {error}")

            return

        self.save_review()

        print("New test case added successfully.")

    # =========================================================
    # DELETE TEST CASE
    # =========================================================

    def delete_test_case(self, case):

        confirmation = input(
            f"Delete {case['test_case_id']}? (Y/N): "
        ).strip().lower()

        if confirmation == "y":

            self.test_cases.remove(case)

            self.save_review()

            print("Test case deleted.")

    # =========================================================
    # REVIEW ONE TEST CASE
    # =========================================================

    def review_one_case(self, case):

        while True:

            self.display_test_case(case)

            print("\n1. Approve")
            print("2. Reject")
            print("3. Edit")
            print("4. Improve using Gemini")
            print("5. Delete")
            print("6. Back")

            choice = input("Choose action: ").strip()

            if choice == "1":

                # Approval requires successful execution.
                execution_status = case.get(
                    "execution_status",
                    "not_executed"
                )

                if execution_status != "passed":

                    print("\nCannot approve this test case.")

                    print(
                        f"Current execution status: {execution_status}"
                    )

                    print(
                        "The test case must pass execution before approval."
                    )

                    continue

                try:

                    self.validate_all_cases()

                except Exception as error:

                    print(f"Cannot approve: {error}")

                    continue

                case["review_status"] = "approved"

                case["reviewed_at"] = datetime.now().isoformat()

                print("Test case approved successfully.")

                break

            elif choice == "2":

                case["review_status"] = "rejected"

                case["rejection_reason"] = input(
                    "Reason for rejection: "
                ).strip()

                break

            elif choice == "3":

                self.edit_test_case(case)

            elif choice == "4":

                try:

                    self.improve_with_ai(case)

                except Exception as error:

                    print(f"AI improvement failed: {error}")

            elif choice == "5":

                self.delete_test_case(case)

                return

            elif choice == "6":

                break

            else:

                print("Invalid choice.")

        case["reviewed_at"] = datetime.now().isoformat()

        self.save_review()

    # =========================================================
    # SAVE REVIEW
    # =========================================================

    def save_review(self):

        self.review_data["test_cases"] = self.test_cases

        self.update_summary()

        self.output_folder.mkdir(
            parents=True,
            exist_ok=True
        )

        self.review_data["updated_at"] = datetime.now().isoformat()

        with open(
            self.review_file,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                self.review_data,
                file,
                indent=4,
                ensure_ascii=False
            )

        print("\nReview progress saved.")

    # =========================================================
    # REVIEW SUMMARY
    # =========================================================

    def update_summary(self):

        self.review_data["review_summary"] = {

            "total": len(self.test_cases),

            "approved": sum(
                c.get("review_status") == "approved"
                for c in self.test_cases
            ),

            "rejected": sum(
                c.get("review_status") == "rejected"
                for c in self.test_cases
            ),

            "pending": sum(
                c.get("review_status") == "pending"
                for c in self.test_cases
            ),

            "passed_execution": sum(
                c.get("execution_status") == "passed"
                for c in self.test_cases
            ),

            "failed_execution": sum(
                c.get("execution_status") == "failed"
                for c in self.test_cases
            ),

            "blocked_execution": sum(
                c.get("execution_status") == "blocked"
                for c in self.test_cases
            ),

            "not_executed": sum(
                c.get("execution_status", "not_executed") == "not_executed"
                for c in self.test_cases
            )
        }

    # =========================================================
    # EXPORT APPROVED TEST CASES
    # =========================================================

    def export_approved_cases(self):

        approved = [
            case for case in self.test_cases
            if (
                case.get("review_status") == "approved"
                and case.get("execution_status") == "passed"
            )
        ]

        if not approved:

            print("No approved test cases available.")

            return

        workbook = Workbook()

        sheet = workbook.active
        sheet.title = "Approved Test Cases"

        headers = [
            "Test Case ID",
            "Module",
            "Scenario",
            "Type",
            "Priority",
            "Preconditions",
            "Test Steps",
            "Expected Results",
            "Source Workflows",
            "Evidence"
        ]

        sheet.append(headers)

        for cell in sheet[1]:

            cell.font = Font(
                bold=True,
                color="FFFFFF"
            )

            cell.fill = PatternFill(
                fill_type="solid",
                fgColor="1F4E78"
            )

        for case in approved:

            sheet.append([
                case["test_case_id"],
                case["module"],
                case["scenario_name"],
                case["scenario_type"],
                case["priority"],
                "\n".join(case["preconditions"]),
                "\n".join(case["test_steps"]),
                "\n".join(case["expected_results"]),
                ", ".join(case["source_workflow_ids"]),
                "\n".join(case["evidence"])
            ])

        widths = [
            16, 20, 35, 18, 12,
            40, 50, 50, 35, 45
        ]

        for index, width in enumerate(widths, 1):

            sheet.column_dimensions[
                sheet.cell(row=1, column=index).column_letter
            ].width = width

        for row in sheet.iter_rows(min_row=2):

            for cell in row:

                cell.alignment = Alignment(
                    vertical="top",
                    wrap_text=True
                )

        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = sheet.dimensions

        workbook.save(self.approved_excel)

        print(
            f"\nApproved Excel exported: {self.approved_excel}"
        )

        print(f"Exported test cases: {len(approved)}")

    # =========================================================
    # DISPLAY SUMMARY
    # =========================================================

    def display_summary(self):

        self.update_summary()

        summary = self.review_data["review_summary"]

        print("\n========== REVIEW SUMMARY ==========")

        print(f"Total: {summary['total']}")
        print(f"Approved: {summary['approved']}")
        print(f"Rejected: {summary['rejected']}")
        print(f"Pending: {summary['pending']}")

        print("\n========== EXECUTION SUMMARY ==========")

        print(
            f"Passed: {summary['passed_execution']}"
        )

        print(
            f"Failed: {summary['failed_execution']}"
        )

        print(
            f"Blocked: {summary['blocked_execution']}"
        )

        print(
            f"Not Executed: {summary['not_executed']}"
        )

        print("====================================")

    # =========================================================
    # MAIN MENU
    # =========================================================

    def run(self):

        print("\nStarting Test Case Review Agent...")

        self.load_test_cases()

        while True:

            print("\n========== MAIN MENU ==========")

            print("1. View all test cases")
            print("2. Review a test case")
            print("3. Add new test case")
            print("4. Export approved test cases")
            print("5. Review summary")
            print("6. Save and exit")

            choice = input("\nSelect option: ").strip()

            if choice == "1":

                print("\n========== ALL TEST CASES ==========")

                for case in self.test_cases:

                    print(
                        f"{case['test_case_id']} | "
                        f"{case['scenario_name']} | "
                        f"Execution: "
                        f"{case.get('execution_status', 'not_executed')} | "
                        f"Review: "
                        f"{case.get('review_status', 'pending')}"
                    )

            elif choice == "2":

                test_id = input(
                    "Enter test case ID: "
                ).strip()

                case = next(
                    (
                        item for item in self.test_cases
                        if item["test_case_id"] == test_id
                    ),
                    None
                )

                if case:

                    self.review_one_case(case)

                else:

                    print("Test case not found.")

            elif choice == "3":

                self.add_manual_test_case()

            elif choice == "4":

                self.export_approved_cases()

            elif choice == "5":

                self.display_summary()

            elif choice == "6":

                self.save_review()

                self.display_summary()

                print("\nReview session completed.")

                break

            else:

                print("Invalid selection.")


# =============================================================
# APPLICATION ENTRY POINT
# =============================================================

def main():

    try:

        agent = TestCaseReviewAgent()

        agent.run()

    except Exception as error:

        print(f"\nTest Case Review failed: {error}")

        raise


if __name__ == "__main__":

    main()
