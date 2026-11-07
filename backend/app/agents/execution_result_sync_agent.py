
import json
import shutil

from pathlib import Path
from datetime import datetime, timezone


PROJECT_ROOT = Path(__file__).resolve().parents[3]

TEST_CASES_FILE = (
    PROJECT_ROOT
    / "generated"
    / "test_cases"
    / "reviewed_test_cases.json"
)

BATCH_REPORT_FILE = (
    PROJECT_ROOT
    / "generated"
    / "action_plans"
    / "batch_execution_report.json"
)

ACTION_PLANS_DIR = (
    PROJECT_ROOT
    / "generated"
    / "action_plans"
)

BACKUP_DIR = (
    PROJECT_ROOT
    / "generated"
    / "test_cases"
    / "backups"
)


class ExecutionResultSyncAgent:

    def load_json(self, file_path):

        if not file_path.exists():
            raise FileNotFoundError(
                f"File not found: {file_path}"
            )

        with open(file_path, "r", encoding="utf-8") as file:
            return json.load(file)

    def save_json(self, file_path, data):

        with open(
            file_path,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                data,
                file,
                indent=4
            )

    def get_cases(self, data):

        if isinstance(data, list):
            return data, None

        if isinstance(data, dict):

            if isinstance(data.get("test_cases"), list):
                return data["test_cases"], "test_cases"

            if isinstance(data.get("cases"), list):
                return data["cases"], "cases"

        raise ValueError(
            "Unexpected reviewed test cases JSON structure."
        )

    def synchronize(self):

        print("\n===================================")
        print(" EXECUTION RESULT SYNCHRONIZATION")
        print("===================================")

        reviewed_data = self.load_json(
            TEST_CASES_FILE
        )

        batch_report = self.load_json(
            BATCH_REPORT_FILE
        )

        cases, cases_key = self.get_cases(
            reviewed_data
        )

        batch_results = batch_report.get(
            "results",
            []
        )

        if not isinstance(batch_results, list):
            raise ValueError(
                "Batch report results must be a list."
            )

        # Create a backup before modifying reviewed cases.

        BACKUP_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        timestamp = datetime.now(
            timezone.utc
        ).strftime("%Y%m%d_%H%M%S")

        backup_file = (
            BACKUP_DIR
            / f"reviewed_test_cases_{timestamp}.json"
        )

        shutil.copy2(
            TEST_CASES_FILE,
            backup_file
        )

        case_lookup = {
            case.get("test_case_id"): case
            for case in cases
            if case.get("test_case_id")
        }

        updated = 0
        passed = 0
        failed = 0
        skipped = 0
        errors = []

        processed_ids = set()

        for batch_item in batch_results:

            test_case_id = batch_item.get(
                "test_case_id"
            )

            if not test_case_id:
                errors.append(
                    "Batch result has no test_case_id."
                )
                continue

            if test_case_id in processed_ids:
                errors.append(
                    f"Duplicate batch result: {test_case_id}"
                )
                continue

            processed_ids.add(test_case_id)

            case = case_lookup.get(test_case_id)

            if case is None:
                errors.append(
                    f"Test case not found: {test_case_id}"
                )
                continue

            report_status = str(
                batch_item.get("status", "")
            ).lower()

            result_file = batch_item.get(
                "result_file"
            )

            if (
                not result_file
                or Path(result_file).name != result_file
            ):
                errors.append(
                    f"Invalid result file for {test_case_id}"
                )
                continue

            result_path = (
                ACTION_PLANS_DIR
                / result_file
            )

            if not result_path.exists():

                errors.append(
                    f"Execution result missing for {test_case_id}"
                )

                case["execution_status"] = "error"

                case["execution_result"] = {
                    "test_case_id": test_case_id,
                    "status": "error",
                    "error": "Individual execution result file missing."
                }

                if case.get("review_status") == "approved":
                    case["review_status"] = "pending"

                failed += 1
                updated += 1
                continue

            try:

                execution_result = self.load_json(
                    result_path
                )

                detail_status = str(
                    execution_result.get("status", "")
                ).lower()

                # Never accept a passing batch result if
                # the individual result does not also pass.

                if (
                    report_status == "passed"
                    and detail_status != "passed"
                ):
                    final_status = "error"

                    error_message = (
                        "Batch report and individual result "
                        "statuses do not match."
                    )

                    errors.append(
                        f"{test_case_id}: {error_message}"
                    )

                elif report_status in (
                    "passed",
                    "failed",
                    "timeout",
                    "error"
                ) and report_status == detail_status:

                    final_status = report_status

                else:

                    final_status = "error"

                    error_message = (
                        "Invalid or inconsistent execution status."
                    )

                    errors.append(
                        f"{test_case_id}: {error_message}"
                    )

                case["execution_status"] = final_status

                case["execution_result"] = execution_result

                case["execution_metadata"] = {
                    "executed_at": batch_report.get(
                        "executed_at"
                    ),
                    "action_plan_file": (
                        f"{test_case_id}_ai.json"
                    ),
                    "result_file": result_file,
                    "return_code": batch_item.get(
                        "return_code"
                    ),
                    "synchronized_at": datetime.now(
                        timezone.utc
                    ).isoformat()
                }

                # Failed executions cannot retain approval.

                if final_status != "passed":

                    if case.get("review_status") == "approved":
                        case["review_status"] = "pending"

                    failed += 1

                else:
                    passed += 1

                updated += 1

                print(
                    f"{test_case_id}: "
                    f"{final_status.upper()}"
                )

            except Exception as error:

                errors.append(
                    f"{test_case_id}: {str(error)}"
                )

                case["execution_status"] = "error"

                if case.get("review_status") == "approved":
                    case["review_status"] = "pending"

                failed += 1
                updated += 1

        # Preserve the original JSON structure.

        if cases_key:
            reviewed_data[cases_key] = cases
            output_data = reviewed_data
        else:
            output_data = cases

        self.save_json(
            TEST_CASES_FILE,
            output_data
        )

        summary = {
            "synchronized_at": datetime.now(
                timezone.utc
            ).isoformat(),

            "total_batch_results": len(batch_results),

            "updated": updated,

            "passed": passed,

            "failed": failed,

            "skipped": skipped,

            "errors": errors,

            "backup_file": str(backup_file)
        }

        sync_report_file = (
            ACTION_PLANS_DIR
            / "execution_sync_report.json"
        )

        self.save_json(
            sync_report_file,
            summary
        )

        print("\n===================================")
        print(" SYNCHRONIZATION SUMMARY")
        print("===================================")

        print(f"Updated: {updated}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Errors: {len(errors)}")

        print(
            f"\nBackup: {backup_file}"
        )

        print(
            f"Sync report: {sync_report_file}"
        )

        return summary


if __name__ == "__main__":

    agent = ExecutionResultSyncAgent()

    agent.synchronize()
