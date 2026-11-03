
import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path


class HumanReviewAgent:

    def __init__(self):

        self.project_root = Path(__file__).resolve().parents[3]

        self.input_file = (
            self.project_root
            / "generated"
            / "application_maps"
            / "business_logic_analysis.json"
        )

        self.output_file = (
            self.project_root
            / "generated"
            / "application_maps"
            / "reviewed_business_logic.json"
        )

        self.analysis = {}
        self.review = {}

    def load_analysis(self):
        """Load the original Gemini analysis."""

        if not self.input_file.exists():

            raise FileNotFoundError(
                f"Business analysis not found: {self.input_file}"
            )

        with open(
            self.input_file,
            "r",
            encoding="utf-8"
        ) as file:

            self.analysis = json.load(file)

        self.validate_analysis()

        # Preserve the original AI output
        self.review = {
            "review_id": datetime.now().strftime(
                "%Y%m%d_%H%M%S"
            ),

            "created_at": datetime.now().isoformat(),

            "original_analysis": deepcopy(self.analysis),

            "reviewed_workflows": [],

            "reviewed_test_scenarios": [],

            "additional_business_requirements": [],

            "review_summary": {}
        }

        print("\nOriginal AI analysis loaded successfully.")

    def validate_analysis(self):
        """Validate required sections before review."""

        required_sections = [
            "application_overview",
            "pages",
            "business_workflows",
            "potential_test_scenarios"
        ]

        for section in required_sections:

            if section not in self.analysis:

                raise ValueError(
                    f"Missing required section: {section}"
                )

        if not isinstance(
            self.analysis["business_workflows"], list
        ):

            raise ValueError(
                "Business workflows must be a list."
            )

        if not isinstance(
            self.analysis["potential_test_scenarios"], list
        ):

            raise ValueError(
                "Test scenarios must be a list."
            )

    def display_application_overview(self):

        overview = self.analysis["application_overview"]

        print("\n========== APPLICATION OVERVIEW ==========")

        print(f"Name: {overview.get('name', 'Unknown')}")

        print(f"Purpose: {overview.get('purpose', 'Not provided')}")

        print("\nObserved functionality:")

        for item in overview.get(
            "observed_functionality", []
        ):

            print(f"- {item}")

        print("==========================================")

    def get_decision(self):
        """Ask user for an approval decision."""

        while True:

            print("\nChoose an action:")

            print("1. Approve")
            print("2. Reject")
            print("3. Edit")
            print("4. Skip")

            choice = input("Enter choice (1-4): ").strip()

            decisions = {
                "1": "approved",
                "2": "rejected",
                "3": "edit",
                "4": "pending"
            }

            if choice in decisions:

                return decisions[choice]

            print("Invalid choice. Try again.")

    def edit_item(self, item, editable_fields):
        """Allow user to modify selected fields."""

        while True:

            print("\nCurrent information:")

            for index, field in enumerate(
                editable_fields, start=1
            ):

                print(
                    f"{index}. {field}: "
                    f"{item.get(field, 'Not provided')}"
                )

            print("0. Finish editing")

            choice = input(
                "\nSelect field number to edit: "
            ).strip()

            if choice == "0":

                break

            try:

                field_index = int(choice) - 1

                field = editable_fields[field_index]

            except (ValueError, IndexError):

                print("Invalid field selection.")

                continue

            current_value = item.get(field)

            print(f"\nCurrent {field}: {current_value}")

            if isinstance(current_value, list):

                print(
                    "Enter one item per line. "
                    "Type DONE on a new line to finish."
                )

                new_values = []

                while True:

                    value = input("> ").strip()

                    if value.upper() == "DONE":

                        break

                    if value:

                        new_values.append(value)

                item[field] = new_values

            else:

                new_value = input(
                    "Enter new value: "
                ).strip()

                if new_value:

                    item[field] = new_value

            print(f"{field} updated successfully.")

        return item

    def review_workflows(self):

        workflows = self.analysis["business_workflows"]

        print("\n========== BUSINESS WORKFLOW REVIEW ==========")

        for index, workflow in enumerate(
            workflows, start=1
        ):

            print(f"\nWorkflow {index}:")
            print(f"Name: {workflow.get('workflow_name')}")
            print(f"Description: {workflow.get('description')}")

            print("\nSteps:")

            for step in workflow.get("steps", []):

                print(f"- {step}")

            print(
                f"\nAI Confidence: "
                f"{workflow.get('confidence', 'unknown')}"
            )

            decision = self.get_decision()

            if decision == "edit":

                workflow = self.edit_item(
                    workflow,
                    [
                        "workflow_name",
                        "description",
                        "steps"
                    ]
                )

                print("\nAfter editing:")

                print(
                    json.dumps(
                        workflow,
                        indent=4,
                        ensure_ascii=False
                    )
                )

                decision = self.get_decision()

                if decision == "edit":

                    print(
                        "Please approve, reject or skip "
                        "after completing edits."
                    )

                    decision = self.get_decision()

            workflow_review = {
                "workflow_id": f"WF-{index:03d}",
                "workflow": workflow,
                "review_status": (
                    decision if decision != "edit"
                    else "pending"
                ),
                "reviewed_at": datetime.now().isoformat()
            }

            self.review["reviewed_workflows"].append(
                workflow_review
            )

        print("\nWorkflow review completed.")

    def review_test_scenarios(self):

        scenarios = self.analysis["potential_test_scenarios"]

        print("\n========== TEST SCENARIO REVIEW ==========")

        for index, scenario in enumerate(
            scenarios, start=1
        ):

            print(f"\nScenario {index}:")

            print(
                f"ID: {scenario.get('scenario_id')}"
            )

            print(
                f"Name: {scenario.get('scenario_name')}"
            )

            print(
                f"Type: {scenario.get('scenario_type')}"
            )

            print("\nTest Steps:")

            for step in scenario.get("test_steps", []):

                print(f"- {step}")

            print("\nExpected Results:")

            for result in scenario.get(
                "expected_results", []
            ):

                print(f"- {result}")

            print(
                f"\nAI Confidence: "
                f"{scenario.get('confidence', 'unknown')}"
            )

            decision = self.get_decision()

            if decision == "edit":

                scenario = self.edit_item(
                    scenario,
                    [
                        "scenario_name",
                        "scenario_type",
                        "preconditions",
                        "test_steps",
                        "expected_results"
                    ]
                )

                print("\nUpdated scenario:")

                print(
                    json.dumps(
                        scenario,
                        indent=4,
                        ensure_ascii=False
                    )
                )

                decision = self.get_decision()

                if decision == "edit":

                    print(
                        "Please make a final approval decision."
                    )

                    decision = self.get_decision()

            scenario_review = {
                "scenario_id": scenario.get(
                    "scenario_id",
                    f"AI-{index:03d}"
                ),

                "scenario": scenario,

                "review_status": (
                    decision if decision != "edit"
                    else "pending"
                ),

                "reviewed_at": datetime.now().isoformat()
            }

            self.review[
                "reviewed_test_scenarios"
            ].append(scenario_review)

        print("\nTest scenario review completed.")

    def add_business_requirements(self):

        print("\n========== ADD BUSINESS REQUIREMENTS ==========")

        while True:

            requirement = input(
                "\nEnter additional business requirement "
                "(or DONE to finish): "
            ).strip()

            if requirement.upper() == "DONE":

                break

            if requirement:

                self.review[
                    "additional_business_requirements"
                ].append({

                    "requirement_id": (
                        f"USER-{len(self.review['additional_business_requirements']) + 1:03d}"
                    ),

                    "description": requirement,

                    "status": "pending_confirmation",

                    "created_at": datetime.now().isoformat()

                })

                print("Requirement added successfully.")

    def generate_summary(self):

        workflows = self.review["reviewed_workflows"]

        scenarios = self.review["reviewed_test_scenarios"]

        self.review["review_summary"] = {

            "total_workflows": len(workflows),

            "approved_workflows": sum(
                item["review_status"] == "approved"
                for item in workflows
            ),

            "rejected_workflows": sum(
                item["review_status"] == "rejected"
                for item in workflows
            ),

            "pending_workflows": sum(
                item["review_status"] == "pending"
                for item in workflows
            ),

            "total_test_scenarios": len(scenarios),

            "approved_test_scenarios": sum(
                item["review_status"] == "approved"
                for item in scenarios
            ),

            "rejected_test_scenarios": sum(
                item["review_status"] == "rejected"
                for item in scenarios
            ),

            "pending_test_scenarios": sum(
                item["review_status"] == "pending"
                for item in scenarios
            ),

            "additional_requirements": len(
                self.review["additional_business_requirements"]
            )
        }

    def save_review(self):

        self.output_file.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        self.review["updated_at"] = datetime.now().isoformat()

        self.generate_summary()

        with open(
            self.output_file,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                self.review,
                file,
                indent=4,
                ensure_ascii=False
            )

        print(
            f"\nReview saved successfully: {self.output_file}"
        )

    def display_summary(self):

        summary = self.review["review_summary"]

        print("\n========== REVIEW SUMMARY ==========")

        for key, value in summary.items():

            print(
                f"{key.replace('_', ' ').title()}: {value}"
            )

        print("====================================")

    def run(self):

        print("\nStarting Human Review Agent...")

        self.load_analysis()

        self.display_application_overview()

        self.review_workflows()

        self.review_test_scenarios()

        self.add_business_requirements()

        self.save_review()

        self.display_summary()

        print("\nHuman review process completed.")


def main():

    try:

        agent = HumanReviewAgent()

        agent.run()

    except Exception as error:

        print(f"\nHuman Review Agent failed: {error}")


if __name__ == "__main__":

    main()
