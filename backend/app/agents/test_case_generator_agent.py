import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

from backend.app.ai.gemini_client import GeminiClient
from backend.app.generators.test_case_validator import TestCaseValidator


class TestCaseGeneratorAgent:

    def __init__(self):

        # Project root directory.
        self.project_root = Path(__file__).resolve().parents[3]

        # Input and output files.
        self.input_file = (
            self.project_root
            / "generated"
            / "application_maps"
            / "reviewed_business_logic.json"
        )

        self.output_directory = (
            self.project_root
            / "generated"
            / "test_cases"
        )

        self.json_output = (
            self.output_directory / "test_cases.json"
        )

        self.excel_output = (
            self.output_directory / "test_cases.xlsx"
        )

        self.validator = TestCaseValidator()
        self.gemini = GeminiClient()

    # --------------------------------------------------
    # LOAD REVIEWED BUSINESS LOGIC
    # --------------------------------------------------

    def load_reviewed_business_logic(self):

        if not self.input_file.exists():
            raise FileNotFoundError(
                f"Reviewed business logic not found: {self.input_file}"
            )

        with open(
            self.input_file,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        print("\nReviewed business logic loaded successfully.")

        return data

    # --------------------------------------------------
    # GET APPROVED WORKFLOWS
    # --------------------------------------------------

    def get_approved_workflows(self, data):

        approved_workflows = []

        for item in data.get("reviewed_workflows", []):

            if item.get("review_status") != "approved":
                continue

            workflow = item.get("workflow", {})

            if not isinstance(workflow, dict):
                continue

            approved_workflows.append({
                "workflow_id": item.get("workflow_id"),
                "workflow": workflow
            })

        print(
            f"Approved workflows found: {len(approved_workflows)}"
        )

        return approved_workflows

    # --------------------------------------------------
    # GET APPROVED TEST SCENARIOS
    # --------------------------------------------------

    def get_approved_scenarios(self, data):

        approved_scenarios = []

        for item in data.get("reviewed_test_scenarios", []):

            # Only explicitly approved scenarios are included.
            if item.get("review_status") != "approved":
                continue

            scenario = item.get("scenario", {})

            if not isinstance(scenario, dict):
                continue

            approved_scenarios.append(scenario)

        print(
            f"Approved test scenarios found: {len(approved_scenarios)}"
        )

        return approved_scenarios

    # --------------------------------------------------
    # GET CONFIRMED ADDITIONAL REQUIREMENTS
    # --------------------------------------------------

    def get_confirmed_requirements(self, data):

        confirmed_requirements = []

        requirements = data.get(
            "additional_business_requirements",
            []
        )

        for requirement in requirements:

            if isinstance(requirement, str):
                confirmed_requirements.append(requirement)
                continue

            if not isinstance(requirement, dict):
                continue

            status = (
                requirement.get("review_status")
                or requirement.get("status")
            )

            if status in ["confirmed", "approved"]:

                confirmed_requirements.append(requirement)

        return confirmed_requirements

    # --------------------------------------------------
    # EXTRACT URLS FROM WORKFLOW OR SCENARIO
    # --------------------------------------------------

    def extract_urls(self, value):

        found_urls = []

        if isinstance(value, dict):

            for child in value.values():
                found_urls.extend(self.extract_urls(child))

        elif isinstance(value, list):

            for child in value:
                found_urls.extend(self.extract_urls(child))

        elif isinstance(value, str):

            urls = re.findall(
                r"https?://[^\s'\"<>]+",
                value
            )

            found_urls.extend(urls)

        return found_urls

    # --------------------------------------------------
    # MATCH SCENARIO WITH ITS WORKFLOW
    # --------------------------------------------------

    def match_workflows(self, scenario, approved_workflows):

        scenario_urls = self.extract_urls(scenario)

        scenario_hosts = {
            urlparse(url.rstrip(".,;)")).hostname
            for url in scenario_urls
            if urlparse(url.rstrip(".,;)")).hostname
        }

        matched_workflow_ids = []

        for item in approved_workflows:

            workflow_id = item.get("workflow_id")
            workflow = item.get("workflow", {})

            workflow_urls = self.extract_urls(workflow)

            workflow_hosts = {
                urlparse(url.rstrip(".,;)")).hostname
                for url in workflow_urls
                if urlparse(url.rstrip(".,;)")).hostname
            }

            if scenario_hosts.intersection(workflow_hosts):

                if workflow_id:
                    matched_workflow_ids.append(workflow_id)

        return matched_workflow_ids

    # --------------------------------------------------
    # BUILD GEMINI PROMPT
    # --------------------------------------------------

    def build_prompt(
        self,
        scenario,
        linked_workflows,
        confirmed_requirements
    ):

        prompt = f"""
You are an experienced Senior QA Automation Engineer.

Your task is to convert ONE human-approved test scenario
into ONE detailed, structured manual test case.

IMPORTANT RULES:

1. Generate exactly one test case.
2. Do not invent application functionality.
3. Use only the supplied scenario, workflow and evidence.
4. Keep the original scenario type unchanged.
5. Make test steps clear, sequential and executable.
6. Expected results must be specific and verifiable.
7. Do not invent selectors, URLs, credentials or test data.
8. If information is unavailable, do not make assumptions.
9. Return valid JSON only. Do not use Markdown code fences.

APPROVED TEST SCENARIO:

{json.dumps(scenario, indent=2, ensure_ascii=False)}

LINKED APPROVED WORKFLOWS:

{json.dumps(linked_workflows, indent=2, ensure_ascii=False)}

CONFIRMED ADDITIONAL REQUIREMENTS:

{json.dumps(confirmed_requirements, indent=2, ensure_ascii=False)}

Return this JSON structure:

{{
    "test_case": {{
        "module": "Application module name",
        "scenario_name": "Original scenario name",
        "scenario_type": "positive",
        "priority": "medium",
        "preconditions": [
            "Precondition 1"
        ],
        "test_steps": [
            "Step 1",
            "Step 2"
        ],
        "expected_results": [
            "Expected result 1"
        ]
    }}
}}

Allowed scenario_type values:
- positive
- negative
- boundary
- ui_validation

Allowed priority values:
- high
- medium
- low

Return exactly one test_case object.
"""

        return prompt

    # --------------------------------------------------
    # PARSE GEMINI RESPONSE
    # --------------------------------------------------

    def parse_gemini_response(self, response):

        cleaned_response = response.strip()

        # Remove Markdown fences if Gemini returns them.
        cleaned_response = re.sub(
            r"^```(?:json)?\s*",
            "",
            cleaned_response
        )

        cleaned_response = re.sub(
            r"\s*```$",
            "",
            cleaned_response
        )

        data = json.loads(cleaned_response)

        if isinstance(data, dict):

            if isinstance(data.get("test_case"), dict):
                return data["test_case"]

            if isinstance(data.get("test_cases"), list):
                if data["test_cases"]:
                    return data["test_cases"][0]

        raise ValueError(
            "Gemini response does not contain a valid test_case object."
        )

    # --------------------------------------------------
    # GENERATE ONE TEST CASE
    # --------------------------------------------------

    def generate_one_test_case(
        self,
        scenario,
        approved_workflows,
        confirmed_requirements,
        sequence
    ):

        scenario_id = scenario.get(
            "scenario_id",
            f"UNKNOWN-{sequence}"
        )

        scenario_name = scenario.get(
            "scenario_name",
            f"Scenario {sequence}"
        )

        print(
            f"\nGenerating test case for {scenario_id}: "
            f"{scenario_name}"
        )

        # Find the approved workflow associated with this scenario.
        workflow_ids = self.match_workflows(
            scenario,
            approved_workflows
        )

        linked_workflows = [
            item
            for item in approved_workflows
            if item.get("workflow_id") in workflow_ids
        ]

        prompt = self.build_prompt(
            scenario,
            linked_workflows,
            confirmed_requirements
        )

        # Ask Gemini to generate the test case.
        response = self.gemini.generate_json(prompt)

        generated = self.parse_gemini_response(response)

        # Preserve the human-approved scenario information.
        generated["test_case_id"] = f"TC-{sequence:03d}"

        generated["scenario_name"] = scenario_name

        generated["scenario_type"] = scenario.get(
            "scenario_type",
            generated.get("scenario_type", "positive")
        )

        # Use safe defaults if Gemini omits optional details.
        generated["module"] = (
            generated.get("module")
            or "General"
        )

        if generated.get("priority") not in [
            "high",
            "medium",
            "low"
        ]:
            generated["priority"] = "medium"

        generated["preconditions"] = (
            generated.get("preconditions")
            or scenario.get("preconditions", [])
        )

        generated["test_steps"] = (
            generated.get("test_steps")
            or scenario.get("test_steps", [])
        )

        generated["expected_results"] = (
            generated.get("expected_results")
            or scenario.get("expected_results", [])
        )

        # Retain workflow traceability.
        generated["source_workflow_ids"] = workflow_ids

        # Retain original scenario evidence.
        generated["evidence"] = list(
            scenario.get("evidence", [])
        )

        generated["evidence"].append(
            f"Approved source scenario: {scenario_id}"
        )

        # These statuses are used by later project steps.
        generated["execution_status"] = "not_executed"
        generated["review_status"] = "pending"

        # Validate before accepting the generated case.
        errors = self.validator.validate_case(generated)

        if errors:

            error_message = "\n".join(errors)

            raise ValueError(
                f"Generated test case {scenario_id} failed validation:\n"
                f"{error_message}"
            )

        print(
            f"Successfully generated {generated['test_case_id']}"
        )

        return generated

    # --------------------------------------------------
    # GENERATE ALL TEST CASES
    # --------------------------------------------------

    def generate_test_cases(self):

        data = self.load_reviewed_business_logic()

        approved_workflows = self.get_approved_workflows(data)

        approved_scenarios = self.get_approved_scenarios(data)

        confirmed_requirements = self.get_confirmed_requirements(data)

        if not approved_scenarios:

            raise ValueError(
                "No approved test scenarios found. "
                "Please approve scenarios in Step 11 first."
            )

        generated_cases = []

        for sequence, scenario in enumerate(
            approved_scenarios,
            start=1
        ):

            try:

                test_case = self.generate_one_test_case(
                    scenario,
                    approved_workflows,
                    confirmed_requirements,
                    sequence
                )

                generated_cases.append(test_case)

            except Exception as error:

                print(
                    f"\nFailed to generate scenario "
                    f"{scenario.get('scenario_id')}: {error}"
                )

        if not generated_cases:

            raise ValueError(
                "Gemini did not generate any valid test cases."
            )

        # Validate all generated cases together.
        errors = self.validator.validate_all(generated_cases)

        if errors:

            raise ValueError(
                "Generated test cases failed final validation:\n"
                + "\n".join(errors)
            )

        return generated_cases

    # --------------------------------------------------
    # EXPORT JSON
    # --------------------------------------------------

    def export_json(self, test_cases):

        self.output_directory.mkdir(
            parents=True,
            exist_ok=True
        )

        output_data = {
            "generated_at": datetime.now().isoformat(),
            "source_file": str(
                self.input_file.relative_to(self.project_root)
            ),
            "total_test_cases": len(test_cases),
            "generation_metadata": {
                "execution_status": "not_executed",
                "generation_engine": "Gemini",
                "approved_scenarios_only": True,
            },
            "test_cases": test_cases,
        }

        with open(
            self.json_output,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                output_data,
                file,
                indent=4,
                ensure_ascii=False
            )

        print(f"\nJSON exported: {self.json_output}")

    # --------------------------------------------------
    # EXPORT EXCEL
    # --------------------------------------------------

    def export_excel(self, test_cases):

        workbook = Workbook()

        sheet = workbook.active
        sheet.title = "Generated Test Cases"

        headers = [
            "Test Case ID",
            "Module",
            "Scenario Name",
            "Scenario Type",
            "Priority",
            "Preconditions",
            "Test Steps",
            "Expected Results",
            "Source Workflow IDs",
            "Evidence",
            "Review Status",
            "Execution Status",
        ]

        sheet.append(headers)

        for cell in sheet[1]:

            cell.font = Font(
                bold=True,
                color="FFFFFF"
            )

            cell.fill = PatternFill(
                fill_type="solid",
                fgColor="1F4E78"
            )

            cell.alignment = Alignment(
                horizontal="center",
                vertical="center",
                wrap_text=True
            )

        for case in test_cases:

            sheet.append([
                case["test_case_id"],
                case["module"],
                case["scenario_name"],
                case["scenario_type"],
                case["priority"],
                "\n".join(case["preconditions"]),
                "\n".join(case["test_steps"]),
                "\n".join(case["expected_results"]),
                ", ".join(case["source_workflow_ids"]),
                "\n".join(case["evidence"]),
                case["review_status"],
                case["execution_status"],
            ])

        # Set readable column widths.
        column_widths = {
            "A": 16,
            "B": 22,
            "C": 45,
            "D": 20,
            "E": 15,
            "F": 45,
            "G": 60,
            "H": 60,
            "I": 25,
            "J": 55,
            "K": 18,
            "L": 20,
        }

        for column, width in column_widths.items():
            sheet.column_dimensions[column].width = width

        # Wrap text in all data cells.
        for row in sheet.iter_rows(min_row=2):

            for cell in row:

                cell.alignment = Alignment(
                    vertical="top",
                    wrap_text=True
                )

        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = sheet.dimensions

        workbook.save(self.excel_output)

        print(f"Excel exported: {self.excel_output}")

    # --------------------------------------------------
    # MAIN EXECUTION
    # --------------------------------------------------

    def run(self):

        print("\n==========================================")
        print("AI TEST CASE GENERATOR")
        print("==========================================")

        print("\nReading approved business logic...")

        test_cases = self.generate_test_cases()

        print("\nExporting generated test cases...")

        self.export_json(test_cases)
        self.export_excel(test_cases)

        print("\n==========================================")
        print("TEST CASE GENERATION COMPLETED")
        print("==========================================")

        print(
            f"\nTotal generated test cases: {len(test_cases)}"
        )

        print("\nGenerated files:")

        print(self.json_output)
        print(self.excel_output)


def main():

    try:

        agent = TestCaseGeneratorAgent()
        agent.run()

    except Exception as error:

        print(
            f"\nTest Case Generation failed: {error}"
        )


if __name__ == "__main__":
    main()