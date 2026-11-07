
import json
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]

DEFAULT_AUDIT_FILE = (
    PROJECT_ROOT
    / "generated"
    / "reports"
    / "self_healing_audit.jsonl"
)


def build_locator(page, definition):
    """
    Build a Python Playwright locator from locator metadata.
    """

    strategy = definition["strategy"]
    value = definition["value"]
    options = definition.get("options", {})

    if strategy == "getByPlaceholder":
        return page.get_by_placeholder(value, **options)

    if strategy == "getByLabel":
        return page.get_by_label(value, **options)

    if strategy == "getByTestId":
        return page.get_by_test_id(value)

    if strategy == "getByRole":
        role = definition.get("role", "button")
        return page.get_by_role(role, name=value, **options)

    if strategy == "css":
        return page.locator(value)

    raise ValueError(
        f"Unsupported locator strategy: {strategy}"
    )


def write_audit(
    test_case_id,
    element_name,
    status,
    original_locator,
    selected_locator,
    failures,
    audit_file=None
):
    """
    Save locator resolution details as one JSON line.
    """

    output_file = Path(audit_file or DEFAULT_AUDIT_FILE)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "test_case_id": test_case_id,
        "element_name": element_name,
        "status": status,
        "original_locator": original_locator,
        "selected_locator": selected_locator,
        "failed_candidates": failures
    }

    with output_file.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")


async def resolve_self_healing_locator(
    page,
    test_case_id,
    element_name,
    candidates,
    audit_file=None
):
    """
    Resolve a locator safely.

    The first candidate is treated as the original locator.
    Remaining candidates are tried only if the original fails.

    A candidate is accepted only when exactly one visible
    element matches it.
    """

    if not candidates:
        raise ValueError(
            "At least one locator candidate is required."
        )

    original_locator = candidates[0]
    failures = []

    for index, candidate in enumerate(candidates):

        try:
            locator = build_locator(page, candidate)

            count = await locator.count()

            if count != 1:
                failures.append({
                    "locator": candidate,
                    "reason": (
                        f"Expected exactly one match, found {count}"
                    )
                })
                continue

            visible = await locator.is_visible()

            if not visible:
                failures.append({
                    "locator": candidate,
                    "reason": "Element is not visible"
                })
                continue

            status = (
                "HEALED"
                if index > 0
                else "ORIGINAL_LOCATOR_WORKED"
            )

            write_audit(
                test_case_id=test_case_id,
                element_name=element_name,
                status=status,
                original_locator=original_locator,
                selected_locator=candidate,
                failures=failures,
                audit_file=audit_file
            )

            if index > 0:
                print(
                    f"[SELF-HEALING] {test_case_id}: "
                    f"{element_name} locator replaced."
                )

            return locator

        except Exception as error:

            failures.append({
                "locator": candidate,
                "reason": str(error)
            })

    write_audit(
        test_case_id=test_case_id,
        element_name=element_name,
        status="HEALING_FAILED",
        original_locator=original_locator,
        selected_locator=None,
        failures=failures,
        audit_file=audit_file
    )

    raise RuntimeError(
        f"Self-healing failed for {test_case_id}: "
        f"{element_name}. No safe locator was found."
    )
