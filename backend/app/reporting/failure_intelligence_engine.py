
import json
import re
from pathlib import Path
from datetime import datetime


# ==================================================
# PROJECT PATHS
# ==================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]

PLAYWRIGHT_REPORT = (
    PROJECT_ROOT
    / "generated"
    / "frameworks"
    / "playwright_project"
    / "playwright-report.json"
)

TRACEABILITY_REPORT = (
    PROJECT_ROOT
    / "generated"
    / "reports"
    / "test_traceability_report.json"
)

OUTPUT_DIRECTORY = PROJECT_ROOT / "generated" / "reports"

OUTPUT_FILE = (
    OUTPUT_DIRECTORY / "failure_intelligence_report.json"
)


# ==================================================
# LOAD JSON
# ==================================================

def load_json(file_path):

    if not file_path.exists():
        raise FileNotFoundError(
            f"File not found: {file_path}"
        )

    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


# ==================================================
# EXTRACT TEST CASE ID
# ==================================================

def extract_test_case_id(title):

    if not isinstance(title, str):
        return None

    match = re.search(r"\bTC-\d+\b", title)

    return match.group(0) if match else None


# ==================================================
# NORMALIZE ERROR
# ==================================================

def normalize_error(error):

    if isinstance(error, str):
        return {
            "message": error,
            "stack": None
        }

    if not isinstance(error, dict):
        return {
            "message": str(error),
            "stack": None
        }

    return {
        "message": error.get("message"),
        "stack": error.get("stack"),
        "location": error.get("location")
    }


# ==================================================
# EXTRACT FAILED STEPS
# ==================================================

def extract_failed_steps(steps):

    failed_steps = []

    for step in steps:

        if not isinstance(step, dict):
            continue

        error = step.get("error")

        if error:

            failed_steps.append({

                "step_title": step.get("title"),

                "category": step.get("category"),

                "duration": step.get("duration"),

                "error": normalize_error(error)

            })

        # Playwright steps can contain nested steps.

        nested_steps = step.get("steps", [])

        failed_steps.extend(
            extract_failed_steps(nested_steps)
        )

    return failed_steps


# ==================================================
# EXTRACT ATTACHMENTS
# ==================================================

def extract_attachments(attachments):

    extracted = []

    for attachment in attachments:

        if not isinstance(attachment, dict):
            continue

        extracted.append({

            "name": attachment.get("name"),

            "content_type": attachment.get("contentType"),

            "path": attachment.get("path"),

            "body_available": bool(
                attachment.get("body")
            )

        })

    return extracted


# ==================================================
# IDENTIFY FAILED ASSERTION
# ==================================================

def identify_failed_assertion(message):

    if not message:
        return None

    lines = message.splitlines()

    for line in lines:

        cleaned = line.strip()

        if (
            cleaned.startswith("Error:")
            or "expect(" in cleaned
            or "Expected:" in cleaned
            or "Received:" in cleaned
        ):

            return cleaned

    return lines[0].strip() if lines else None


# ==================================================
# ANALYZE ONE PLAYWRIGHT RESULT
# ==================================================

def analyze_result(result):

    errors = [
        normalize_error(error)
        for error in result.get("errors", [])
    ]

    steps = extract_failed_steps(
        result.get("steps", [])
    )

    attachments = extract_attachments(
        result.get("attachments", [])
    )

    messages = [
        error["message"]
        for error in errors
        if error.get("message")
    ]

    failure_message = (
        "\n".join(messages)
        if messages else None
    )

    assertion = identify_failed_assertion(
        failure_message
    )

    return {

        "status": result.get("status"),

        "duration": result.get("duration"),

        "failure_reason": failure_message,

        "failed_assertion": assertion,

        "errors": errors,

        "failed_steps": steps,

        "stack_traces": [
            error["stack"]
            for error in errors
            if error.get("stack")
        ],

        "attachments": attachments,

        "screenshots": [
            attachment
            for attachment in attachments
            if (
                attachment.get("content_type") == "image/png"
                or attachment.get("content_type") == "image/jpeg"
                or "screenshot" in str(
                    attachment.get("name", "")
                ).lower()
            )
        ]

    }


# ==================================================
# WALK THROUGH PLAYWRIGHT SUITES
# ==================================================

def collect_test_results(report):

    collected = {}

    def walk_suites(suites):

        for suite in suites:

            for spec in suite.get("specs", []):

                title = spec.get("title", "")

                test_case_id = extract_test_case_id(title)

                if not test_case_id:
                    continue

                for test in spec.get("tests", []):

                    for result in test.get("results", []):

                        status = result.get("status")

                        if status not in (
                            "failed",
                            "timedOut",
                            "passed"
                        ):
                            continue

                        analyzed = analyze_result(result)

                        collected.setdefault(
                            test_case_id,
                            []
                        ).append({

                            "playwright_title": title,

                            **analyzed

                        })

            walk_suites(
                suite.get("suites", [])
            )

    walk_suites(report.get("suites", []))

    return collected


# ==================================================
# BUILD FAILURE INTELLIGENCE
# ==================================================

def build_failure_report(traceability, collected):

    failure_records = []

    for case in traceability.get("traceability", []):

        test_case_id = case.get("test_case_id")

        status = case.get("execution_status")

        if status not in ("FAILED", "FLAKY"):
            continue

        attempts = collected.get(test_case_id, [])

        failure_records.append({

            "test_case_id": test_case_id,

            "scenario_name": case.get("scenario_name"),

            "module": case.get("module"),

            "priority": case.get("priority"),

            "execution_status": status,

            "attempt_details": attempts,

            "failure_count": sum(
                1
                for attempt in attempts
                if attempt["status"] in (
                    "failed",
                    "timedOut"
                )
            ),

            "screenshot_count": sum(
                len(attempt["screenshots"])
                for attempt in attempts
            )

        })

    return failure_records


# ==================================================
# GENERATE SUMMARY
# ==================================================

def generate_summary(records):

    return {

        "total_failure_records": len(records),

        "failed_test_cases": sum(
            1 for record in records
            if record["execution_status"] == "FAILED"
        ),

        "flaky_test_cases": sum(
            1 for record in records
            if record["execution_status"] == "FLAKY"
        ),

        "total_failed_attempts": sum(
            record["failure_count"]
            for record in records
        ),

        "total_screenshots": sum(
            record["screenshot_count"]
            for record in records
        )

    }


# ==================================================
# MAIN
# ==================================================

def main():

    print("\nStarting Failure Intelligence Engine...\n")

    playwright_report = load_json(
        PLAYWRIGHT_REPORT
    )

    traceability = load_json(
        TRACEABILITY_REPORT
    )

    collected = collect_test_results(
        playwright_report
    )

    failure_records = build_failure_report(
        traceability,
        collected
    )

    summary = generate_summary(
        failure_records
    )

    final_report = {

        "generated_at": datetime.now().astimezone().isoformat(),

        "summary": summary,

        "failure_details": failure_records

    }

    OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            final_report,
            file,
            indent=4
        )

    print("======================================")
    print("FAILURE INTELLIGENCE REPORT")
    print("======================================")

    print(json.dumps(summary, indent=4))

    for record in failure_records:

        print(
            f"\nTest Case: {record['test_case_id']}"
        )

        print(
            f"Status: {record['execution_status']}"
        )

        for attempt in record["attempt_details"]:

            print(
                f"Attempt Status: {attempt['status']}"
            )

            print(
                f"Failure: {attempt['failure_reason']}"
            )

    print("\nReport generated successfully!")

    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
