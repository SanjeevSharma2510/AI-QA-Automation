
import asyncio
import json
from datetime import datetime
from pathlib import Path

from backend.app.browser.browser_manager import BrowserManager


class UIDiscoveryEngine:

    def __init__(self, page):
        self.page = page

    async def discover_elements(self, selector, script):
        """Discover visible elements matching a CSS selector."""

        return await self.page.locator(selector).evaluate_all(script)

    async def discover_navigation(self):
        """Discover navigation menus and their links."""

        return await self.discover_elements(
            "nav, [role='navigation'], [role='menubar']",
            """
            elements => elements.map((element, index) => ({
                index: index + 1,
                label: element.getAttribute("aria-label"),
                text: (element.innerText || "").trim(),
                links: Array.from(
                    element.querySelectorAll("a[href]")
                ).map(link => ({
                    text: (link.innerText || "").trim(),
                    href: link.href
                }))
            }))
            """
        )

    async def discover_buttons(self):
        """Discover buttons and their attributes."""

        return await self.discover_elements(
            "button, input[type='button'], input[type='submit'], [role='button']",
            """
            elements => elements
                .filter(element => {
                    const style = getComputedStyle(element);
                    return style.display !== "none" &&
                           style.visibility !== "hidden" &&
                           element.getClientRects().length > 0;
                })
                .map((element, index) => ({
                    index: index + 1,
                    tag: element.tagName.toLowerCase(),
                    text: (
                        element.innerText ||
                        element.value ||
                        element.getAttribute("aria-label") ||
                        ""
                    ).trim(),
                    id: element.id,
                    name: element.getAttribute("name"),
                    type: element.getAttribute("type"),
                    role: element.getAttribute("role"),
                    disabled: element.disabled,
                    aria_label: element.getAttribute("aria-label")
                }))
            """
        )

    async def discover_inputs(self):
        """Discover input fields, textareas and their properties."""

        return await self.discover_elements(
            "input, textarea",
            """
            elements => elements
                .filter(element => {
                    const style = getComputedStyle(element);
                    return style.display !== "none" &&
                           style.visibility !== "hidden" &&
                           element.getClientRects().length > 0 &&
                           !["hidden", "button", "submit", "reset", "image"]
                               .includes(element.type);
                })
                .map((element, index) => ({
                    index: index + 1,
                    tag: element.tagName.toLowerCase(),
                    type: element.type || "textarea",
                    id: element.id,
                    name: element.name,
                    placeholder: element.placeholder,
                    label: Array.from(element.labels || [])
                        .map(label => label.innerText.trim()),
                    required: element.required,
                    disabled: element.disabled,
                    readonly: element.readOnly,
                    value_present: Boolean(element.value),
                    aria_label: element.getAttribute("aria-label")
                }))
            """
        )

    async def discover_dropdowns(self):
        """Discover native select dropdowns and their options."""

        return await self.discover_elements(
            "select",
            """
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
                    multiple: element.multiple,
                    disabled: element.disabled,
                    selected_values: Array.from(element.selectedOptions)
                        .map(option => option.value),
                    options: Array.from(element.options).map(option => ({
                        text: option.text.trim(),
                        value: option.value,
                        selected: option.selected,
                        disabled: option.disabled
                    }))
                }))
            """
        )

    async def discover_checkboxes_and_radios(self):
        """Discover checkboxes and radio buttons."""

        return await self.discover_elements(
            "input[type='checkbox'], input[type='radio']",
            """
            elements => elements
                .filter(element => {
                    const style = getComputedStyle(element);
                    return style.display !== "none" &&
                           style.visibility !== "hidden" &&
                           element.getClientRects().length > 0;
                })
                .map((element, index) => ({
                    index: index + 1,
                    type: element.type,
                    id: element.id,
                    name: element.name,
                    value: element.value,
                    checked: element.checked,
                    disabled: element.disabled
                }))
            """
        )

    async def discover_tabs(self):
        """Discover tab controls and their selected state."""

        return await self.discover_elements(
            "[role='tab'], button[aria-selected], [aria-controls][role='tab']",
            """
            elements => elements
                .filter(element => {
                    const style = getComputedStyle(element);
                    return style.display !== "none" &&
                           style.visibility !== "hidden" &&
                           element.getClientRects().length > 0;
                })
                .map((element, index) => ({
                    index: index + 1,
                    text: (element.innerText || "").trim(),
                    id: element.id,
                    role: element.getAttribute("role"),
                    selected: element.getAttribute("aria-selected"),
                    controls: element.getAttribute("aria-controls"),
                    disabled: element.disabled || false
                }))
            """
        )

    async def discover_dialogs(self):
        """Discover currently visible dialogs and modals."""

        return await self.discover_elements(
            "[role='dialog'], dialog[open], [aria-modal='true']",
            """
            elements => elements
                .filter(element => {
                    const style = getComputedStyle(element);
                    return style.display !== "none" &&
                           style.visibility !== "hidden" &&
                           element.getClientRects().length > 0;
                })
                .map((element, index) => ({
                    index: index + 1,
                    role: element.getAttribute("role"),
                    title: element.getAttribute("aria-label") ||
                           element.getAttribute("aria-labelledby"),
                    text: (element.innerText || "").trim()
                }))
            """
        )

    async def discover_tables(self):
        """Discover tables, headers, rows and pagination controls."""

        tables = await self.discover_elements(
            "table",
            """
            elements => elements
                .filter(element => {
                    const style = getComputedStyle(element);
                    return style.display !== "none" &&
                           style.visibility !== "hidden" &&
                           element.getClientRects().length > 0;
                })
                .map((table, index) => ({
                    index: index + 1,
                    id: table.id,
                    headers: Array.from(
                        table.querySelectorAll("thead th")
                    ).map(th => th.innerText.trim()),
                    row_count: table.querySelectorAll("tbody tr").length,
                    rows: Array.from(
                        table.querySelectorAll("tbody tr")
                    ).slice(0, 10).map(row =>
                        Array.from(row.cells).map(cell =>
                            cell.innerText.trim()
                        )
                    )
                }))
            """
        )

        pagination = await self.discover_elements(
            "[aria-label*='page' i], [class*='pagination'] button, "
            "[class*='pagination'] a, [role='navigation'] button",
            """
            elements => elements
                .filter(element => {
                    const style = getComputedStyle(element);
                    return style.display !== "none" &&
                           style.visibility !== "hidden" &&
                           element.getClientRects().length > 0;
                })
                .map(element => ({
                    text: (
                        element.innerText ||
                        element.getAttribute("aria-label") ||
                        ""
                    ).trim(),
                    disabled: element.disabled || false,
                    aria_label: element.getAttribute("aria-label")
                }))
            """
        )

        return {
            "tables": tables,
            "pagination_controls": pagination
        }

    async def discover_menus(self):
        """Discover menu containers and their visible items."""

        return await self.discover_elements(
            "[role='menu'], [role='menubar'], [role='menuitem']",
            """
            elements => elements
                .filter(element => {
                    const style = getComputedStyle(element);
                    return style.display !== "none" &&
                           style.visibility !== "hidden" &&
                           element.getClientRects().length > 0;
                })
                .map((element, index) => ({
                    index: index + 1,
                    role: element.getAttribute("role"),
                    text: (element.innerText || "").trim(),
                    aria_expanded: element.getAttribute("aria-expanded")
                }))
            """
        )

    async def explore(self):
        """Run all UI discovery operations."""

        print("\\nStarting advanced UI discovery...")

        result = {
            "discovery_time": datetime.now().isoformat(),

            "website": {
                "title": await self.page.title(),
                "url": self.page.url
            },

            "navigation": await self.discover_navigation(),
            "menus": await self.discover_menus(),
            "buttons": await self.discover_buttons(),
            "inputs": await self.discover_inputs(),
            "dropdowns": await self.discover_dropdowns(),
            "checkboxes_and_radios":
                await self.discover_checkboxes_and_radios(),
            "tabs": await self.discover_tabs(),
            "dialogs": await self.discover_dialogs(),
            "table_information": await self.discover_tables()
        }

        result["summary"] = {
            "navigation_sections": len(result["navigation"]),
            "menus": len(result["menus"]),
            "buttons": len(result["buttons"]),
            "inputs": len(result["inputs"]),
            "dropdowns": len(result["dropdowns"]),
            "checkboxes_and_radios":
                len(result["checkboxes_and_radios"]),
            "tabs": len(result["tabs"]),
            "dialogs": len(result["dialogs"]),
            "tables": len(result["table_information"]["tables"])
        }

        return result

    def save_report(self, result):
        """Save the UI discovery report."""

        project_root = Path(__file__).resolve().parents[3]

        output_folder = (
            project_root / "generated" / "application_maps"
        )

        output_folder.mkdir(parents=True, exist_ok=True)

        report_path = output_folder / "ui_discovery_report.json"

        with open(report_path, "w", encoding="utf-8") as file:
            json.dump(
                result,
                file,
                indent=4,
                ensure_ascii=False
            )

        print(f"\\nUI discovery report saved: {report_path}")

    def display_summary(self, result):
        """Print discovered UI element counts."""

        print("\\n========== UI DISCOVERY SUMMARY ==========")

        for name, count in result["summary"].items():
            print(f"{name.replace('_', ' ').title()}: {count}")

        print("===========================================")


async def main():

    browser_manager = BrowserManager()

    try:

        # Launch browser
        page = await browser_manager.start_browser()

        # Open demo website
        await browser_manager.open_website(
            "https://demo.playwright.dev/todomvc/"
        )

        # Initialize discovery engine
        discovery_engine = UIDiscoveryEngine(page)

        # Discover UI elements
        result = await discovery_engine.explore()

        # Display summary
        discovery_engine.display_summary(result)

        # Save JSON report
        discovery_engine.save_report(result)

        await asyncio.sleep(3)

    except Exception as error:

        print(f"UI discovery failed: {error}")

    finally:

        await browser_manager.close_browser()


if __name__ == "__main__":
    asyncio.run(main())
