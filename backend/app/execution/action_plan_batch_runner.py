
import json
import subprocess
import sys

from pathlib import Path
from datetime import datetime, timezone


PROJECT_ROOT = Path(__file__).resolve().parents[3]

ACTION_PLANS_DIR = (
    PROJECT_ROOT
    / "generated"
    / "action_plans"
)

BATCH_REPORT_FILE = (
    ACTION_PLANS_DIR
    / "batch_execution_report.json"
)


def execute_all_plans():

    plan_files = sorted(
        ACTION_PLANS_DIR.glob("*_ai.json")
    )

    if not plan_files:

        raise FileNotFoundError(
            "No AI-generated action plans found."
        )

    print("\n===================================")
    print(" AI ACTION PLAN BATCH EXECUTOR")
    print("===================================")

    print(f"Plans found: {len(plan_files)}")

    results = []

    for index, plan_file in enumerate(plan_files, start=1):

        test_case_id = plan_file.stem.replace(
            "_ai", ""
        )

        original_result_file = (
            ACTION_PLANS_DIR
            / f"{test_case_id}_results.json"
        )

        ai_result_file = (
            ACTION_PLANS_DIR
            / f"{test_case_id}_ai_results.json"
        )

        # Preserve the existing manual execution result.
        original_result = None

        if original_result_file.exists():

            original_result = (
                original_result_file.read_bytes()
            )

        print("\n-----------------------------------")
        print(
            f"[{index}/{len(plan_files)}] "
            f"Executing {test_case_id}"
        )
        print("-----------------------------------")

        command = [
            sys.executable,
            "-m",
            "backend.app.execution.action_plan_runner",
            "--plan",
            plan_file.name
        ]

        try:

            process = subprocess.run(
                command,
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=600
            )

            # Read the result produced by the existing runner.
            execution_data = None

            if original_result_file.exists():

                with open(
                    original_result_file,
                    "r",
                    encoding="utf-8"
                ) as file:

                    execution_data = json.load(file)

                # Save AI execution results separately.
                with open(
                    ai_result_file,
                    "w",
                    encoding="utf-8"
                ) as file:

                    json.dump(
                        execution_data,
                        file,
                        indent=4
                    )

            if (
                execution_data
                and execution_data.get("status") == "passed"
                and process.returncode == 0
            ):

                status = "passed"

            else:

                status = "failed"

            results.append({
                "test_case_id": test_case_id,
                "status": status,
                "return_code": process.returncode,
                "result_file": (
                    ai_result_file.name
                    if ai_result_file.exists()
                    else None
                ),
                "error": (
                    execution_data.get("error")
                    if execution_data
                    else process.stderr[-2000:]
                )
            })

            print(f"Result: {status.upper()}")

            if process.stdout:
                print(process.stdout[-2000:])

            if process.stderr and status == "failed":
                print(process.stderr[-2000:])

        except subprocess.TimeoutExpired:

            results.append({
                "test_case_id": test_case_id,
                "status": "timeout",
                "return_code": None,
                "result_file": None,
                "error": "Execution exceeded 600 seconds."
            })

            print("Result: TIMEOUT")

        except Exception as error:

            results.append({
                "test_case_id": test_case_id,
                "status": "error",
                "return_code": None,
                "result_file": None,
                "error": str(error)
            })

            print(f"Result: ERROR - {error}")

        finally:

            # Restore the previous manual result file.
            if original_result is not None:

                original_result_file.write_bytes(
                    original_result
                )

            elif original_result_file.exists():

                original_result_file.unlink()

    passed_count = sum(
        1 for item in results
        if item["status"] == "passed"
    )

    failed_count = sum(
        1 for item in results
        if item["status"] == "failed"
    )

    timeout_count = sum(
        1 for item in results
        if item["status"] == "timeout"
    )

    error_count = sum(
        1 for item in results
        if item["status"] == "error"
    )

    report = {
        "executed_at": datetime.now(
            timezone.utc
        ).isoformat(),

        "total_plans": len(plan_files),

        "passed": passed_count,

        "failed": failed_count,

        "timeout": timeout_count,

        "errors": error_count,

        "results": results
    }

    with open(
        BATCH_REPORT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            report,
            file,
            indent=4
        )

    print("\n===================================")
    print(" BATCH EXECUTION SUMMARY")
    print("===================================")

    print(f"Total:   {len(plan_files)}")
    print(f"Passed:  {passed_count}")
    print(f"Failed:  {failed_count}")
    print(f"Timeout: {timeout_count}")
    print(f"Errors:  {error_count}")

    print(
        f"\nReport saved: {BATCH_REPORT_FILE}"
    )

    return report


if __name__ == "__main__":

    execute_all_plans()
