
import asyncio
import json
from datetime import datetime
from pathlib import Path

from backend.app.browser.browser_manager import BrowserManager
from backend.app.restrictions.interaction_policy import InteractionPolicy


class WorkflowDiscoveryEngine:

    def __init__(
        self,
        page,
        approved_dropdowns=None,
        approved_tabs=None
    ):

        self.page = page

        self.policy = InteractionPolicy(
            approved_dropdowns=approved_dropdowns,
            approved_tabs=approved_tabs
        )

        self.workflow_steps = []

    async def capture_state(self):
        """Capture the current visible application state."""

        return await self.page.evaluate("""
            () => {

                const isVisible = element => {

                    const style = getComputedStyle(element);

                    return style.display !== "none" &&
                           style.visibility !== "hidden" &&
                           element.getClientRects().length > 0;
                };

                const elements = Array.from(
                    document.querySelectorAll(
                        "a, button, input, select, textarea, "
                        + "[role='tab'], [role='button'], table"
                    )
                ).filter(isVisible);

                return {

                    url: location.href,

                    title: document.title,

                    visible_elements: elements.map(element => ({

                        tag: element.tagName.toLowerCase(),

                        id: element.id,

                        name: element.getAttribute("name"),

                        type: element.getAttribute("type"),

                        role: element.getAttribute("role"),

                        text: (
                            element.innerText ||
                            element.value ||
                            element.getAttribute("aria-label") ||
                            ""
                        ).trim(),

                        value: element.value || null,

                        disabled: element.disabled || false,

                        selected: element.getAttribute("aria-selected"),

                        row_count: element.tagName === "TABLE"
                            ? element.querySelectorAll("tbody tr").length
                            : null

                    }))
                };
            }
        """)

    def compare_states(self, before, after):
        """Identify changes between two application states."""

        def create_key(element):

            return (
                element["tag"],
                element["id"],
                element["name"],
                element["type"],
                element["text"]
            )

        before_elements = before["visible_elements"]
        after_elements = after["visible_elements"]

        before_map = {
            create_key(element): element
            for element in before_elements
        }

        after_map = {
            create_key(element): element
            for element in after_elements
        }

        before_keys = set(before_map)
        after_keys = set(after_map)

        newly_visible = [
            after_map[key]
            for key in after_keys - before_keys
        ]

        no_longer_visible = [
            before_map[key]
            for key in before_keys - after_keys
        ]

        modified = []

        for key in before_keys & after_keys:

            old_element = before_map[key]
            new_element = after_map[key]

            if (
                old_element["value"] != new_element["value"]
                or old_element["selected"] != new_element["selected"]
                or old_element["disabled"] != new_element["disabled"]
                or old_element["row_count"] != new_element["row_count"]
            ):

                modified.append({
                    "element": new_element,
                    "previous_value": old_element["value"],
                    "current_value": new_element["value"],
                    "previous_selected": old_element["selected"],
                    "current_selected": new_element["selected"],
                    "previous_row_count": old_element["row_count"],
                    "current_row_count": new_element["row_count"]
                })

        return {
            "newly_visible": newly_visible,
            "no_longer_visible": no_longer_visible,
            "modified": modified,
            "url_changed": before["url"] != after["url"],
            "title_changed": before["title"] != after["title"]
        }

    async def execute_dropdown(self, selector, value):
        """Execute an explicitly approved dropdown selection."""

        if not self.policy.can_interact_with_dropdown(selector):

            return {
                "status": "blocked",
                "reason": "Dropdown not approved."
            }

        locator = self.page.locator(selector)

        if await locator.count() != 1:

            return {
                "status": "failed",
                "reason": "Dropdown selector must match exactly one element."
            }

        if not await locator.is_visible():

            return {
                "status": "failed",
                "reason": "Dropdown is not visible."
            }

        if not await locator.is_enabled():

            return {
                "status": "failed",
                "reason": "Dropdown is disabled."
            }

        options = await locator.locator("option").evaluate_all("""
            elements => elements.map(option => ({
                value: option.value,
                disabled: option.disabled
            }))
        """)

        valid_values = [
            option["value"]
            for option in options
            if not option["disabled"]
        ]

        if value not in valid_values:

            return {
                "status": "failed",
                "reason": "Requested option is unavailable."
            }

        previous_value = await locator.input_value()

        if previous_value == value:

            return {
                "status": "skipped",
                "reason": "Dropdown already has the requested value."
            }

        await locator.select_option(value=value)

        return {
            "status": "success",
            "action": "select_dropdown",
            "selector": selector,
            "previous_value": previous_value,
            "selected_value": await locator.input_value()
        }

    async def execute_tab(self, selector):
        """Click an explicitly approved tab."""

        if not self.policy.can_click_tab(selector):

            return {
                "status": "blocked",
                "reason": "Tab not approved."
            }

        locator = self.page.locator(selector)

        if await locator.count() != 1:

            return {
                "status": "failed",
                "reason": "Tab selector must match exactly one element."
            }

        if not await locator.is_visible():

            return {
                "status": "failed",
                "reason": "Tab is not visible."
            }

        if not await locator.is_enabled():

            return {
                "status": "failed",
                "reason": "Tab is disabled."
            }

        role = await locator.get_attribute("role")

        if role != "tab":

            return {
                "status": "blocked",
                "reason": "Only elements with role='tab' are supported."
            }

        if await locator.get_attribute("aria-selected") == "true":

            return {
                "status": "skipped",
                "reason": "Tab is already selected."
            }

        await locator.click()

        return {
            "status": "success",
            "action": "click_tab",
            "selector": selector,
            "selected": await locator.get_attribute("aria-selected")
        }

    async def record_interaction(self, action):
        """Capture before and after states for an interaction."""

        print(f"\nExecuting action: {action}")

        before_state = await self.capture_state()

        action_type = action["type"]

        if action_type == "select_dropdown":

            action_result = await self.execute_dropdown(
                action["selector"],
                action["value"]
            )

        elif action_type == "click_tab":

            action_result = await self.execute_tab(
                action["selector"]
            )

        else:

            action_result = {
                "status": "blocked",
                "reason": "Unsupported interaction type."
            }

        if action_result["status"] != "success":

            return {
                "action": action,
                "result": action_result,
                "state_changes": None
            }

        # Allow dynamic UI updates to complete
        await self.page.wait_for_timeout(1000)

        after_state = await self.capture_state()

        changes = self.compare_states(
            before_state,
            after_state
        )

        step = {
            "step_number": len(self.workflow_steps) + 1,
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "result": action_result,
            "before_state": before_state,
            "after_state": after_state,
            "state_changes": changes
        }

        self.workflow_steps.append(step)

        print("Interaction recorded successfully.")

        print(
            f"New elements: {len(changes['newly_visible'])}"
        )

        print(
            f"Modified elements: {len(changes['modified'])}"
        )

        return step

    async def discover(self, approved_actions):
        """Execute and record a sequence of approved actions."""

        print("\nStarting workflow discovery...")

        initial_state = await self.capture_state()

        for action in approved_actions:

            result = await self.record_interaction(action)

            if result["result"]["status"] == "success":

                continue

            print(
                f"Action not executed: "
                f"{result['result']['reason']}"
            )

        final_state = await self.capture_state()

        return {
            "workflow_name": "Website Dynamic Workflow",
            "discovery_time": datetime.now().isoformat(),

            "website": {
                "initial_url": initial_state["url"],
                "initial_title": initial_state["title"]
            },

            "initial_state": initial_state,

            "steps": self.workflow_steps,

            "final_state": final_state,

            "summary": {
                "total_actions": len(approved_actions),
                "successful_steps": len(self.workflow_steps),
                "failed_or_blocked_actions": (
                    len(approved_actions) - len(self.workflow_steps)
                )
            }
        }

    def save_report(self, report):
        """Save workflow discovery report."""

        project_root = Path(__file__).resolve().parents[3]

        output_folder = (
            project_root / "generated" / "application_maps"
        )

        output_folder.mkdir(
            parents=True,
            exist_ok=True
        )

        report_path = output_folder / "workflow_discovery.json"

        with open(report_path, "w", encoding="utf-8") as file:

            json.dump(
                report,
                file,
                indent=4,
                ensure_ascii=False
            )

        print(f"\nWorkflow report saved: {report_path}")

    def display_summary(self, report):

        print("\n========== WORKFLOW SUMMARY ==========")

        print(
            f"Total actions: "
            f"{report['summary']['total_actions']}"
        )

        print(
            f"Successful steps: "
            f"{report['summary']['successful_steps']}"
        )

        print(
            f"Failed/blocked actions: "
            f"{report['summary']['failed_or_blocked_actions']}"
        )

        for step in report["steps"]:

            print(
                f"Step {step['step_number']}: "
                f"{step['action']['type']} - "
                f"{step['result']['status']}"
            )

        print("======================================")


async def main():

    browser_manager = BrowserManager()

    try:

        # Step 1: Launch browser
        page = await browser_manager.start_browser()

        # Step 2: Open demo page
        await browser_manager.open_website(
            "https://demoqa.com/select-menu"
        )

        # Step 3: Configure approved interactions
        engine = WorkflowDiscoveryEngine(
            page=page,
            approved_dropdowns=["#oldSelectMenu"],
            approved_tabs=[]
        )

        # Step 4: Define explicitly approved actions
        approved_actions = [
            {
                "type": "select_dropdown",
                "selector": "#oldSelectMenu",
                "value": "1"
            }
        ]

        # Step 5: Discover workflow
        report = await engine.discover(
            approved_actions
        )

        # Step 6: Display summary
        engine.display_summary(report)

        # Step 7: Save report
        engine.save_report(report)

    except Exception as error:

        print(f"Workflow discovery failed: {error}")

    finally:

        await browser_manager.close_browser()


if __name__ == "__main__":

    asyncio.run(main())
