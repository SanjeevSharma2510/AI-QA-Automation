
import os
import json
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
from google import genai
from google.genai import types


# ==================================================
# CONFIGURATION
# ==================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]

INPUT_FILE = (
    PROJECT_ROOT
    / "generated"
    / "reports"
    / "failure_intelligence_report.json"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "generated"
    / "reports"
    / "ai_root_cause_report.json"
)

load_dotenv(PROJECT_ROOT / ".env")

API_KEY = os.getenv("GEMINI_API_KEY")

MODEL = "gemini-3.7-flash"


# ==================================================
# INITIALIZE GEMINI
# ==================================================

if not API_KEY:
    raise ValueError("GEMINI_API_KEY not found in .env")

client = genai.Client(api_key=API_KEY)


# ==================================================
# LOAD FAILURE DATA
# ==================================================

def load_failure_data():

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Failure report not found: {INPUT_FILE}"
        )

    with open(INPUT_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


# ==================================================
# PREPARE AI PROMPT
# ==================================================

def create_prompt(failure_record):

    return f"""
You are an expert Senior QA Automation Engineer.

Analyze the following actual Playwright test failure evidence.

FAILURE DATA:
{json.dumps(failure_record, indent=2)}

Your tasks:

1. Identify the most probable root cause.
2. Classify the failure into exactly one category:
   - APPLICATION_BUG
   - LOCATOR_ISSUE
   - TIMING_ISSUE
   - TEST_DATA_ISSUE
   - ENVIRONMENT_ISSUE
   - ASSERTION_MISMATCH
   - UNKNOWN

3. Explain the root cause in simple language.
4. Identify the actual evidence supporting your diagnosis.
5. Recommend a practical fix.
6. Decide whether manual investigation is required.
7. Provide a confidence score between 0 and 100.

IMPORTANT RULES:

- Use only the supplied failure evidence.
- Never invent missing selectors, error messages or application behavior.
- Do not assume every timeout is a locator issue.
- If evidence is insufficient, select UNKNOWN.
- Do not modify or execute any test scripts.
- Clearly distinguish confirmed facts from probable causes.

Return ONLY valid JSON using this structure:

{{
    "test_case_id": "TC-001",
    "failure_category": "LOCATOR_ISSUE",
    "root_cause": "Explanation of the probable root cause",
    "evidence": [
        "Evidence from actual execution"
    ],
    "recommended_fix": "Suggested corrective action",
    "confidence": 85,
    "manual_investigation_required": false,
    "analysis_status": "COMPLETED"
}}
"""


# ==================================================
# ANALYZE ONE FAILURE USING GEMINI
# ==================================================

def analyze_failure(failure_record):

    prompt = create_prompt(failure_record)

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.2,
            response_mime_type="application/json"
        )
    )

    if not response.text:
        raise ValueError("Gemini returned an empty response")

    result = json.loads(response.text)

    # Validate mandatory fields and types.

    required_fields = [
        "test_case_id",
        "failure_category",
        "root_cause",
        "evidence",
        "recommended_fix",
        "confidence",
        "manual_investigation_required",
        "analysis_status"
    ]

    for field in required_fields:
        if field not in result:
            raise ValueError(
                f"Gemini response missing field: {field}"
            )

    if not isinstance(result["confidence"], (int, float)):
        raise ValueError("Invalid confidence score")

    result["confidence"] = max(
        0,
        min(100, result["confidence"])
    )

    if not isinstance(result["evidence"], list):
        raise ValueError("Evidence must be a list")

    result["test_case_id"] = failure_record["test_case_id"]

    return result


# ==================================================
# PROCESS ALL FAILURE RECORDS
# ==================================================

def process_failures(data):

    failure_records = data.get("failure_details", [])

    results = []

    for index, failure in enumerate(failure_records, start=1):

        print(
            f"\nAnalyzing failure {index}/{len(failure_records)}: "
            f"{failure.get('test_case_id')}"
        )

        try:

            analysis = analyze_failure(failure)

            results.append(analysis)

            print("Root cause analysis completed.")

        except Exception as error:

            print(f"Analysis failed: {error}")

            results.append({

                "test_case_id": failure.get("test_case_id"),

                "failure_category": "UNKNOWN",

                "root_cause": "AI analysis could not be completed.",

                "evidence": [],

                "recommended_fix": "Review the original Playwright failure evidence.",

                "confidence": 0,

                "manual_investigation_required": True,

                "analysis_status": "FAILED"

            })

    return results


# ==================================================
# SAVE AI ANALYSIS
# ==================================================

def save_report(results):

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    report = {

        "generated_at": datetime.now().astimezone().isoformat(),

        "model": MODEL,

        "total_failures_analyzed": len(results),

        "successful_analyses": sum(
            1 for item in results
            if item["analysis_status"] == "COMPLETED"
        ),

        "failed_analyses": sum(
            1 for item in results
            if item["analysis_status"] == "FAILED"
        ),

        "root_cause_analysis": results

    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:

        json.dump(
            report,
            file,
            indent=4
        )

    return report


# ==================================================
# MAIN
# ==================================================

def main():

    print("\n======================================")
    print("AI FAILURE ROOT CAUSE ANALYZER")
    print("======================================")

    failure_data = load_failure_data()

    failure_records = failure_data.get(
        "failure_details", []
    )

    if not failure_records:

        print("\nNo failed or flaky tests found.")
        print("No Gemini API call required.")

        save_report([])

        return

    results = process_failures(failure_data)

    report = save_report(results)

    print("\n======================================")
    print("AI ROOT CAUSE SUMMARY")
    print("======================================")

    print(json.dumps({

        "total_failures_analyzed":
            report["total_failures_analyzed"],

        "successful_analyses":
            report["successful_analyses"],

        "failed_analyses":
            report["failed_analyses"]

    }, indent=4))

    print("\nReport saved successfully!")

    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
