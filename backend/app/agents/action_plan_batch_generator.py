
import json
from pathlib import Path
from datetime import datetime, timezone

from backend.app.agents.action_plan_generator_agent import (
    ActionPlanGeneratorAgent
)


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

BATCH_REPORT_FILE = (
    ACTION_PLANS_DIR
    / "batch_generation_report.json"
)


def load_reviewed_cases():

    if not REVIEWED_CASES_FILE.exists():
        raise FileNotFoundError(
            f"Reviewed test cases not found: {REVIEWED_CASES_FILE}"
        )

    with open(REVIEWED_CASES_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)

    if isinstance(data, list):
        cases = data

    elif isinstance(data, dict):
        cases = data.get("test_cases", data.get("cases", []))

    else:
        raise ValueError(
            "Unexpected reviewed test cases JSON structure."
        )

    if not isinstance(cases, list):
        raise ValueError(
            "Test cases must be stored in a JSON list."
        )

    return cases


def get_eligible_cases(cases):

    eligible = []

    for case in cases:

        if (
            case.get("review_status") == "approved"
            and case.get("execution_status") == "passed"
        ):

            eligible.append(case)

    return eligible


def generate_all_plans():

    ACTION_PLANS_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    cases = load_reviewed_cases()

    eligible_cases = get_eligible_cases(cases)

    print("\n===================================")
    print(" AI ACTION PLAN BATCH GENERATOR")
    print("===================================")

    print(f"Total test cases: {len(cases)}")
    print(f"Eligible test cases: {len(eligible_cases)}")

    generator = ActionPlanGeneratorAgent()

    results = []

    for index, case in enumerate(eligible_cases, start=1):

        test_case_id = case.get("test_case_id")

        print("\n-----------------------------------")
        print(
            f"[{index}/{len(eligible_cases)}] "
            f"Generating plan for {test_case_id}"
        )
        print("-----------------------------------")

        try:

            plan = generator.generate(test_case_id)

            results.append({
                "test_case_id": test_case_id,
                "status": "generated",
                "action_count": len(plan.get("actions", [])),
                "plan_file": (
                    f"{test_case_id}_ai.json"
                ),
                "error": None
            })

            print(f"SUCCESS: {test_case_id}")

        except Exception as error:

            results.append({
                "test_case_id": test_case_id,
                "status": "failed",
                "action_count": 0,
                "plan_file": None,
                "error": str(error)
            })

            print(f"FAILED: {test_case_id}")
            print(f"Reason: {error}")

    generated_count = sum(
        1 for result in results
        if result["status"] == "generated"
    )

    failed_count = sum(
        1 for result in results
        if result["status"] == "failed"
    )

    report = {
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),

        "total_test_cases": len(cases),

        "eligible_test_cases": len(eligible_cases),

        "generated_count": generated_count,

        "failed_count": failed_count,

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
    print(" BATCH GENERATION SUMMARY")
    print("===================================")

    print(f"Eligible: {len(eligible_cases)}")
    print(f"Generated: {generated_count}")
    print(f"Failed: {failed_count}")

    print(
        f"\nReport saved: {BATCH_REPORT_FILE}"
    )

    return report


if __name__ == "__main__":

    generate_all_plans()
