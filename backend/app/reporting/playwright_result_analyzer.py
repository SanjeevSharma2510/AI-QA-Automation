import json
from pathlib import Path
from datetime import datetime, timezone


PROJECT_ROOT = Path(__file__).resolve().parents[3]

PLAYWRIGHT_PROJECT = (
    PROJECT_ROOT
    / "generated"
    / "frameworks"
    / "playwright_project"
)

INPUT_FILE = PLAYWRIGHT_PROJECT / "playwright-report.json"

OUTPUT_DIR = PROJECT_ROOT / "generated" / "reports"

OUTPUT_FILE = OUTPUT_DIR / "execution_summary.json"


def analyze_results():

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Playwright report not found: {INPUT_FILE}"
        )

    with open(INPUT_FILE, "r", encoding="utf-8") as file:
        report = json.load(file)

    stats = report.get("stats", {})

    expected = stats.get("expected", 0)
    unexpected = stats.get("unexpected", 0)
    skipped = stats.get("skipped", 0)
    flaky = stats.get("flaky", 0)

    total = expected + unexpected + skipped + flaky

    if unexpected > 0:
        overall_status = "failed"
    elif total == 0:
        overall_status = "no_tests"
    else:
        overall_status = "passed"

    summary = {
        "execution_date": datetime.now(timezone.utc).isoformat(),
        "overall_status": overall_status,
        "total_tests": total,
        "passed": expected,
        "failed": unexpected,
        "skipped": skipped,
        "flaky": flaky,
        "source_report": str(INPUT_FILE)
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        json.dump(summary, file, indent=4)

    print("\n========== EXECUTION SUMMARY ==========")

    print(f"Overall Status : {overall_status}")
    print(f"Total Tests    : {total}")
    print(f"Passed         : {expected}")
    print(f"Failed         : {unexpected}")
    print(f"Skipped        : {skipped}")
    print(f"Flaky          : {flaky}")

    print("\nReport saved at:")
    print(OUTPUT_FILE)


if __name__ == "__main__":
    analyze_results()