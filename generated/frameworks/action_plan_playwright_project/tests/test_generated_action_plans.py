
import json
from pathlib import Path

import pytest

from plan_executor import ActionPlanExecutor


TEST_DATA_DIR = (
    Path(__file__).resolve().parents[1]
    / "test_data"
)


PLAN_FILES = sorted(
    TEST_DATA_DIR.glob("*_ai.json")
)


@pytest.mark.parametrize(
    "plan_file",
    PLAN_FILES,
    ids=lambda path: path.stem.replace("_ai", "")
)
def test_generated_action_plan(page, plan_file):

    with open(
        plan_file,
        "r",
        encoding="utf-8"
    ) as file:

        plan = json.load(file)

    print(
        f"\nRunning test case: {plan['test_case_id']}"
    )

    executor = ActionPlanExecutor(page)

    executor.execute_plan(plan)
