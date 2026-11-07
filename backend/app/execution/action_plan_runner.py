
import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

from backend.app.execution.action_executor import ActionExecutor


PROJECT_ROOT = Path(__file__).resolve().parents[3]

PLANS_DIR = PROJECT_ROOT / "generated" / "action_plans"


def run_action_plan(plan_name):

    plan_file = PLANS_DIR / plan_name

    if not plan_file.exists():
        raise FileNotFoundError(
            f"Action plan not found: {plan_file}"
        )

    with open(plan_file, "r", encoding="utf-8") as file:
        plan = json.load(file)

    test_case_id = plan["test_case_id"]

    results = []
    status = "passed"
    error = None

    with sync_playwright() as playwright:

        browser = playwright.chromium.launch(
            headless=False
        )

        page = browser.new_page()

        executor = ActionExecutor(page)

        try:

            for index, action in enumerate(
                plan["actions"],
                start=1
            ):

                print(
                    f"\nExecuting action {index}: "
                    f"{action['action']}"
                )

                result = executor.execute(action)

                results.append(result)

                print("Result:", result)

            print("\nAll actions executed successfully.")

        except Exception as exc:

            status = "failed"
            error = str(exc)

            print("\nAction plan failed:", error)

        finally:

            browser.close()

    output_file = PLANS_DIR / f"{test_case_id}_results.json"

    output = {
        "test_case_id": test_case_id,
        "status": status,
        "results": results,
        "error": error
    }

    with open(output_file, "w", encoding="utf-8") as file:

        json.dump(
            output,
            file,
            indent=4
        )

    print(f"\nResults saved to: {output_file}")

    if status == "failed":
        raise RuntimeError(
            f"Action plan failed for {test_case_id}: {error}"
        )


if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--plan",
        required=True,
        help="Action plan JSON filename"
    )

    args = parser.parse_args()

    run_action_plan(args.plan)
