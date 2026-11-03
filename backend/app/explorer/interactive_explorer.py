
import asyncio
import json
from datetime import datetime
from pathlib import Path

from backend.app.browser.browser_manager import BrowserManager
from backend.app.restrictions.interaction_policy import InteractionPolicy


class InteractiveExplorer:

    def __init__(self, page, approved_dropdowns=None):

        self.page = page

        self.policy = InteractionPolicy(
            approved_selectors=approved_dropdowns
        )

        self.interaction_results = []

    async def capture_page_state(self):
        """
        Capture visible interactive elements before and after interaction.
        """

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
                        "input, select, textarea, button, a, [role='button'], [role='tab']"
                    )
                ).filter(isVisible);

                return {
                    url: window.location.href,
                    title: document.title,

                    visible_elements: elements.map(element => ({
                        tag: element.tagName.toLowerCase(),
                        type: element.type || null,
                        text: (
                            element.innerText ||
                            element.value ||
                            element.getAttribute("aria-label") ||
                            ""
                        ).trim(),
                        id: element.id,
                        name: element.getAttribute("name"),
                        value: element.value || null,
                        disabled: element.disabled || false
                    }))
                };
            }
        """)

    async def discover_native_dropdowns(self):
        """
        Discover visible native HTML select elements.
        """

        return await self.page.locator("select").evaluate_all("""
            elements => elements
                .filter(element => {
                    const style = getComputedStyle(element);

                    return style.display !== "none" &&
                           style.visibility !== "hidden" &&
                           element.getClientRects().length > 0;
                })
                .map((element, index) => ({
                    index: index + 1,
                    id: element.id,
                    name: element.name,
                    options: Array.from(element.options).map(option => ({
                        text: option.text.trim(),
                        value: option.value,
                        disabled: option.disabled
                    })),
                    selected_value: element.value
                }))
        """)

    async def inspect_and_select_dropdown(
        self,
        selector,
        option_value
    ):
        """
        Select an explicitly approved option in a native dropdown.
        """

        print(f"\nInspecting dropdown: {selector}")

        # Step 1: Check interaction policy
        if not self.policy.can_interact_with_dropdown(selector):

            return {
                "selector": selector,
                "status": "blocked",
                "reason": "Dropdown is not approved by interaction policy."
            }

        dropdown = self.page.locator(selector)

        # Step 2: Ensure exactly one dropdown matches
        count = await dropdown.count()

        if count != 1:

            return {
                "selector": selector,
                "status": "failed",
                "reason": f"Expected one dropdown but found {count}."
            }

        # Step 3: Verify dropdown visibility
        if not await dropdown.is_visible():

            return {
                "selector": selector,
                "status": "failed",
                "reason": "Dropdown is not visible."
            }

        # Step 4: Read available options
        options = await dropdown.locator("option").evaluate_all("""
            elements => elements.map(option => ({
                text: option.text.trim(),
                value: option.value,
                disabled: option.disabled
            }))
        """)

        # Step 5: Verify requested option exists
        matching_options = [
            option for option in options
            if option["value"] == option_value
            and not option["disabled"]
        ]

        if not matching_options:

            return {
                "selector": selector,
                "status": "failed",
                "reason": f"Approved option '{option_value}' does not exist.",
                "available_options": options
            }

        # Step 6: Capture state before interaction
        before_state = await self.capture_page_state()

        previous_value = await dropdown.input_value()

        # Step 7: Perform approved selection
        try:

            await dropdown.select_option(value=option_value)

            # Allow application event handlers to update the UI
            await self.page.wait_for_timeout(1000)

            # Step 8: Capture state after interaction
            after_state = await self.capture_page_state()

            selected_value = await dropdown.input_value()

            # Step 9: Verify selection
            if selected_value != option_value:

                return {
                    "selector": selector,
                    "status": "failed",
                    "reason": "Selected value did not match expected value.",
                    "expected": option_value,
                    "actual": selected_value
                }

            # Step 10: Compare visible elements
            before_elements = before_state["visible_elements"]
            after_elements = after_state["visible_elements"]

            before_keys = {
                (item["tag"], item["id"], item["name"], item["text"])
                for item in before_elements
            }

            after_keys = {
                (item["tag"], item["id"], item["name"], item["text"])
                for item in after_elements
            }

            newly_visible = after_keys - before_keys
            no_longer_visible = before_keys - after_keys

            result = {
                "selector": selector,
                "status": "success",
                "previous_value": previous_value,
                "selected_value": selected_value,
                "newly_visible_elements": [
                    {
                        "tag": item[0],
                        "id": item[1],
                        "name": item[2],
                        "text": item[3]
                    }
                    for item in sorted(
                        newly_visible,
                        key=lambda item: tuple(
                            str(value or "") for value in item
                        )
                    )
                ],
                "no_longer_visible_elements": [
                    {
                        "tag": item[0],
                        "id": item[1],
                        "name": item[2],
                        "text": item[3]
                    }
                    for item in sorted(
                        no_longer_visible,
                        key=lambda item: tuple(
                            str(value or "") for value in item
                        )
                    )
                ],
                "before_state": before_state,
                "after_state": after_state
            }

            print("Dropdown selection successful!")

            return result

        except Exception as error:

            return {
                "selector": selector,
                "status": "failed",
                "reason": str(error)
            }

    async def explore(self, approved_selections):
        """
        Discover dropdowns and perform only approved selections.

        approved_selections format:
        [
            {"selector": "#oldSelectMenu", "value": "1"}
        ]
        """

        print("\nStarting interactive exploration...")

        initial_state = await self.capture_page_state()

        dropdowns = await self.discover_native_dropdowns()

        print(f"Native dropdowns discovered: {len(dropdowns)}")

        for dropdown in dropdowns:

            print(
                f"Dropdown ID: {dropdown['id']}, "
                f"Options: {len(dropdown['options'])}"
            )

        for selection in approved_selections:

            result = await self.inspect_and_select_dropdown(
                selector=selection["selector"],
                option_value=selection["value"]
            )

            self.interaction_results.append(result)

        final_state = await self.capture_page_state()

        report = {
            "exploration_time": datetime.now().isoformat(),

            "website": {
                "title": await self.page.title(),
                "url": self.page.url
            },

            "initial_state": initial_state,

            "discovered_dropdowns": dropdowns,

            "interaction_results": self.interaction_results,

            "final_state": final_state,

            "summary": {
                "dropdowns_discovered": len(dropdowns),
                "interactions_attempted": len(self.interaction_results),
                "successful_interactions": sum(
                    1 for result in self.interaction_results
                    if result["status"] == "success"
                ),
                "failed_interactions": sum(
                    1 for result in self.interaction_results
                    if result["status"] == "failed"
                ),
                "blocked_interactions": sum(
                    1 for result in self.interaction_results
                    if result["status"] == "blocked"
                )
            }
        }

        return report

    def save_report(self, report):
        """Save interactive exploration results."""

        project_root = Path(__file__).resolve().parents[3]

        output_folder = (
            project_root / "generated" / "application_maps"
        )

        output_folder.mkdir(
            parents=True,
            exist_ok=True
        )

        report_path = (
            output_folder / "interactive_exploration.json"
        )

        with open(report_path, "w", encoding="utf-8") as file:

            json.dump(
                report,
                file,
                indent=4,
                ensure_ascii=False
            )

        print(f"\nReport saved: {report_path}")

    def display_summary(self, report):

        print("\n========== INTERACTIVE EXPLORATION ==========")

        for name, value in report["summary"].items():

            print(f"{name.replace('_', ' ').title()}: {value}")

        print("=============================================")


async def main():

    browser_manager = BrowserManager()

    try:

        # Step 1: Launch browser
        page = await browser_manager.start_browser()

        # Step 2: Open a demo page with native dropdowns
        await browser_manager.open_website(
            "https://demoqa.com/select-menu"
        )

        # Step 3: Configure explicitly approved dropdowns
        explorer = InteractiveExplorer(
            page=page,
            approved_dropdowns=["#oldSelectMenu"]
        )

        # Step 4: Select a specifically approved option
        approved_selections = [
            {
                "selector": "#oldSelectMenu",
                "value": "1"
            }
        ]

        # Step 5: Explore and capture changes
        report = await explorer.explore(
            approved_selections
        )

        # Step 6: Display summary
        explorer.display_summary(report)

        # Step 7: Save report
        explorer.save_report(report)

        await asyncio.sleep(3)

    except Exception as error:

        print(f"Interactive exploration failed: {error}")

    finally:

        await browser_manager.close_browser()


if __name__ == "__main__":

    asyncio.run(main())
