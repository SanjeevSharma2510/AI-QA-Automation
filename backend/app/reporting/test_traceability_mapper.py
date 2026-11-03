
import json
import re
from pathlib import Path
from datetime import datetime


# ==================================================
# PROJECT PATHS
# ==================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]

REVIEWED_FILE = (
    PROJECT_ROOT
    / "generated"
    / "test_cases"
    / "reviewed_test_cases.json"
)

PLAYWRIGHT_REPORT = (
    PROJECT_ROOT
    / "generated"
    / "frameworks"
    / "playwright_project"
    / "playwright-report.json"
)

OUTPUT_DIRECTORY = PROJECT_ROOT / "generated" / "reports"

OUTPUT_FILE = OUTPUT_DIRECTORY / "test_traceability_report.json"


# ==================================================
# LOAD JSON FILES
# ==================================================

def load_json(file_path):

    if not file_path.exists():
        raise FileNotFoundError(
            f"Required file not found: {file_path}"
        )

    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


# ==================================================
# EXTRACT APPROVED TEST CASES
# ==================================================

def extract_approved_cases(data):

    approved_cases = []

    def search_cases(value):

        if isinstance(value, dict):

            if "test_case_id" in value:

                if str(value.get("review_status", "")).lower() == "approved":
                    approved_cases.append(value)

                return

            for child in value.values():
                search_cases(child)

        elif isinstance(value, list):

            for item in value:
                search_cases(item)

    search_cases(data)

    return approved_cases


# ==================================================
# EXTRACT TEST CASE ID FROM PLAYWRIGHT TITLE
# ==================================================

def extract_test_case_id(title):

    if not isinstance(title, str):
        return None

    match = re.search(r"\bTC-\d+\b", title)

    return match.group(0) if match else None


# ==================================================
# EXTRACT PLAYWRIGHT EXECUTION RESULTS
# ==================================================

def extract_playwright_results(report):

    execution_results = {}

    def process_spec(spec):

        title = spec.get("title", "")

        test_case_id = extract_test_case_id(title)

        if not test_case_id:
            return

        tests = spec.get("tests", [])

        if not tests:
            return

        # Usually one test object exists per project.
        # Read all results to identify retries/flaky tests.

        all_statuses = []

        for test in tests:

            results = test.get("results", [])

            for result in results:

                status = result.get("status")

                if status:
                    all_statuses.append(status)

        if not all_statuses:
            final_status = "NOT_EXECUTED"

        elif all_statuses[-1] == "passed":

            if "failed" in all_statuses or "timedOut" in all_statuses:
                final_status = "FLAKY"
            else:
                final_status = "PASSED"

        elif all_statuses[-1] in ("failed", "timedOut"):
            final_status = "FAILED"

        elif all_statuses[-1] == "skipped":
            final_status = "SKIPPED"

        else:
            final_status = "UNKNOWN"

        execution_results[test_case_id] = {
            "playwright_title": title,
            "execution_status": final_status,
            "attempts": len(all_statuses)
        }

    def walk(node):

        if isinstance(node, dict):

            # Playwright JSON reporter stores test specs
            # inside nested suites.

            if "tests" in node and "title" in node:
                process_spec(node)

            for key in ("suites", "specs"):
                children = node.get(key, [])

                if isinstance(children, list):
                    for child in children:
                        walk(child)

        elif isinstance(node, list):

            for item in node:
                walk(item)

    walk(report.get("suites", []))

    return execution_results


# ==================================================
# BUILD TRACEABILITY REPORT
# ==================================================

def build_traceability_report(approved_cases, execution_results):

    traceability = []

    for case in approved_cases:

        test_case_id = case.get("test_case_id")

        execution = execution_results.get(test_case_id)

        if execution:

            execution_status = execution["execution_status"]
            playwright_title = execution["playwright_title"]
            attempts = execution["attempts"]

        else:

            execution_status = "NOT_EXECUTED"
            playwright_title = None
            attempts = 0

        traceability.append({

            "test_case_id": test_case_id,

            "module": case.get("module"),

            "scenario_name": case.get("scenario_name"),

            "priority": case.get("priority"),

            "review_status": case.get("review_status"),

            "execution_status": execution_status,

            "playwright_title": playwright_title,

            "attempts": attempts

        })

    return traceability


# ==================================================
# GENERATE SUMMARY
# ==================================================

def generate_summary(traceability):

    summary = {

        "total_approved": len(traceability),

        "passed": 0,

        "failed": 0,

        "skipped": 0,

        "flaky": 0,

        "not_executed": 0,

        "unknown": 0

    }

    status_mapping = {
        "PASSED": "passed",
        "FAILED": "failed",
        "SKIPPED": "skipped",
        "FLAKY": "flaky",
        "NOT_EXECUTED": "not_executed",
        "UNKNOWN": "unknown"
    }

    for item in traceability:

        key = status_mapping.get(
            item["execution_status"],
            "unknown"
        )

        summary[key] += 1

    return summary


# ==================================================
# SAVE REPORT
# ==================================================

def save_report(report):

    OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:

        json.dump(
            report,
            file,
            indent=4
        )


# ==================================================
# MAIN
# ==================================================

def main():

    print("\nStarting Test Case Traceability Engine...\n")

    reviewed_data = load_json(REVIEWED_FILE)

    playwright_data = load_json(PLAYWRIGHT_REPORT)

    approved_cases = extract_approved_cases(reviewed_data)

    execution_results = extract_playwright_results(
        playwright_data
    )

    traceability = build_traceability_report(
        approved_cases,
        execution_results
    )

    summary = generate_summary(traceability)

    report = {

        "generated_at": datetime.now().astimezone().isoformat(),

        "summary": summary,

        "traceability": traceability

    }

    save_report(report)

    print("======================================")
    print("TEST CASE TRACEABILITY REPORT")
    print("======================================")

    print(json.dumps(summary, indent=4))

    print("\nTraceability details:")

    for item in traceability:

        print(
            f"{item['test_case_id']} | "
            f"{item['scenario_name']} | "
            f"{item['execution_status']}"
        )

    print("\nReport generated successfully!")

    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
