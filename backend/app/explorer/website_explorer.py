
import asyncio
import json
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from backend.app.browser.browser_manager import BrowserManager


class WebsiteExplorer:

    def __init__(self, page):
        self.page = page

    async def inspect_page(self):
        """Inspect the current page and collect UI information."""

        print("\nStarting website exploration...")

        # Basic website information
        title = await self.page.title()
        current_url = self.page.url

        print(f"Website: {title}")
        print(f"URL: {current_url}")

        # JavaScript helper: identify visible elements
        visibility_script = """
            element => {
                const style = window.getComputedStyle(element);

                return (
                    style.display !== "none" &&
                    style.visibility !== "hidden" &&
                    element.getClientRects().length > 0
                );
            }
        """

        # 1. Discover visible links
        links = await self.page.locator("a").evaluate_all("""
            elements => elements
                .filter(element => {
                    const style = window.getComputedStyle(element);
                    return style.display !== "none" &&
                           style.visibility !== "hidden" &&
                           element.getClientRects().length > 0;
                })
                .map(element => ({
                    text: (element.innerText || "").trim(),
                    href: element.href
                }))
                .filter(link => link.href)
        """)

        # 2. Discover visible buttons
        buttons = await self.page.locator(
            "button, input[type='button'], input[type='submit'], [role='button']"
        ).evaluate_all("""
            elements => elements
                .filter(element => {
                    const style = window.getComputedStyle(element);
                    return style.display !== "none" &&
                           style.visibility !== "hidden" &&
                           element.getClientRects().length > 0;
                })
                .map(element => ({
                    tag: element.tagName.toLowerCase(),
                    text: (
                        element.innerText ||
                        element.value ||
                        element.getAttribute("aria-label") ||
                        ""
                    ).trim(),
                    type: element.getAttribute("type"),
                    id: element.id,
                    name: element.getAttribute("name")
                }))
        """)

        # 3. Discover visible input fields
        inputs = await self.page.locator(
            "input:not([type='button']):not([type='submit']), textarea"
        ).evaluate_all("""
            elements => elements
                .filter(element => {
                    const style = window.getComputedStyle(element);
                    return style.display !== "none" &&
                           style.visibility !== "hidden" &&
                           element.getClientRects().length > 0;
                })
                .map(element => ({
                    tag: element.tagName.toLowerCase(),
                    type: element.getAttribute("type") || "textarea",
                    id: element.id,
                    name: element.getAttribute("name"),
                    placeholder: element.getAttribute("placeholder"),
                    required: element.required
                }))
        """)

        # 4. Discover visible dropdowns
        dropdowns = await self.page.locator("select").evaluate_all("""
            elements => elements
                .filter(element => {
                    const style = window.getComputedStyle(element);
                    return style.display !== "none" &&
                           style.visibility !== "hidden" &&
                           element.getClientRects().length > 0;
                })
                .map(element => ({
                    id: element.id,
                    name: element.getAttribute("name"),
                    options: Array.from(element.options).map(option => ({
                        text: option.text,
                        value: option.value
                    }))
                }))
        """)

        # 5. Discover visible tables
        tables = await self.page.locator("table").evaluate_all("""
            elements => elements
                .filter(element => {
                    const style = window.getComputedStyle(element);
                    return style.display !== "none" &&
                           style.visibility !== "hidden" &&
                           element.getClientRects().length > 0;
                })
                .map((table, index) => ({
                    index: index + 1,
                    headers: Array.from(
                        table.querySelectorAll("thead th")
                    ).map(th => th.innerText.trim()),
                    row_count: table.querySelectorAll("tbody tr").length
                }))
        """)

        # Keep only links belonging to the current website
        base_domain = urlparse(current_url).netloc

        internal_links = [
            link for link in links
            if urlparse(link["href"]).netloc == base_domain
        ]

        # Build the exploration result
        result = {
            "exploration_time": datetime.now().isoformat(),
            "website": {
                "title": title,
                "url": current_url,
                "domain": base_domain
            },
            "page_elements": {
                "links": links,
                "internal_links": internal_links,
                "buttons": buttons,
                "inputs": inputs,
                "dropdowns": dropdowns,
                "tables": tables
            },
            "summary": {
                "total_links": len(links),
                "internal_links": len(internal_links),
                "total_buttons": len(buttons),
                "total_inputs": len(inputs),
                "total_dropdowns": len(dropdowns),
                "total_tables": len(tables)
            }
        }

        print("\nExploration completed!")

        return result

    def save_report(self, result):
        """Save exploration results as a JSON file."""

        project_root = Path(__file__).resolve().parents[3]

        output_folder = (
            project_root / "generated" / "application_maps"
        )

        output_folder.mkdir(
            parents=True,
            exist_ok=True
        )

        report_path = output_folder / "website_exploration.json"

        with open(report_path, "w", encoding="utf-8") as file:
            json.dump(result, file, indent=4, ensure_ascii=False)

        print(f"\nExploration report saved: {report_path}")

    def display_summary(self, result):
        """Display a readable summary in the terminal."""

        summary = result["summary"]

        print("\n========== EXPLORATION SUMMARY ==========")
        print(f"Website: {result['website']['title']}")
        print(f"Links found: {summary['total_links']}")
        print(f"Internal links: {summary['internal_links']}")
        print(f"Buttons found: {summary['total_buttons']}")
        print(f"Input fields found: {summary['total_inputs']}")
        print(f"Dropdowns found: {summary['total_dropdowns']}")
        print(f"Tables found: {summary['total_tables']}")
        print("=========================================")


async def main():

    browser_manager = BrowserManager()

    try:
        # Step 1: Launch browser
        page = await browser_manager.start_browser()

        # Step 2: Open demo website
        await browser_manager.open_website(
            "https://demo.playwright.dev/todomvc/"
        )

        # Step 3: Create explorer
        explorer = WebsiteExplorer(page)

        # Step 4: Inspect website
        result = await explorer.inspect_page()

        # Step 5: Display summary
        explorer.display_summary(result)

        # Step 6: Save JSON report
        explorer.save_report(result)

        # Step 7: Keep browser visible briefly
        await asyncio.sleep(5)

    except Exception as error:
        print(f"Exploration failed: {error}")

    finally:
        await browser_manager.close_browser()


if __name__ == "__main__":
    asyncio.run(main())
