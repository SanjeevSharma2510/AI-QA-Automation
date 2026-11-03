
import asyncio
import json
import re
from collections import deque
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse, urldefrag

from backend.app.browser.browser_manager import BrowserManager
from backend.app.explorer.website_explorer import WebsiteExplorer


class MultiPageExplorer:

    def __init__(self, page, start_url, max_pages=20, max_depth=3):

        self.page = page
        self.start_url = start_url
        self.max_pages = max_pages
        self.max_depth = max_depth

        parsed_url = urlparse(start_url)

        self.base_domain = parsed_url.netloc.lower()
        self.base_scheme = parsed_url.scheme.lower()

        # Queue contains (URL, depth)
        self.pending_urls = deque()

        # Tracks already explored URLs
        self.visited_urls = set()

        self.page_results = []
        self.failed_pages = []

        self.explorer = WebsiteExplorer(page)

    def normalize_url(self, url):
        """Normalize URLs to avoid duplicate exploration."""

        parsed = urlparse(url)

        # Remove URL fragments
        url, _ = urldefrag(url)

        # Remove trailing slash except for homepage
        parsed = urlparse(url)

        if parsed.path != "/":
            url = url.rstrip("/")

        return url

    def is_valid_internal_url(self, url):
        """Check whether URL belongs to the same website."""

        parsed = urlparse(url)

        if parsed.scheme not in ("http", "https"):
            return False

        if parsed.netloc.lower() != self.base_domain:
            return False

        # Skip common non-page resources
        excluded_extensions = (
            ".pdf", ".jpg", ".jpeg", ".png",
            ".gif", ".zip", ".xlsx", ".xls",
            ".doc", ".docx", ".csv", ".mp4"
        )

        if parsed.path.lower().endswith(excluded_extensions):
            return False

        # Skip common logout or destructive navigation routes
        restricted_terms = (
            "logout", "signout", "delete",
            "remove", "checkout", "payment"
        )

        if any(term in parsed.path.lower() for term in restricted_terms):
            return False

        return True

    async def discover_links(self):
        """Find internal links on the current page."""

        links = await self.page.locator("a[href]").evaluate_all("""
            elements => elements
                .filter(element => {
                    const style = window.getComputedStyle(element);

                    return style.display !== "none" &&
                           style.visibility !== "hidden" &&
                           element.getClientRects().length > 0;
                })
                .map(element => element.href)
        """)

        valid_links = set()

        for link in links:

            absolute_url = urljoin(self.page.url, link)

            if not self.is_valid_internal_url(absolute_url):
                continue

            normalized_url = self.normalize_url(absolute_url)

            if normalized_url not in self.visited_urls:
                valid_links.add(normalized_url)

        return sorted(valid_links)

    def save_screenshot(self, url):
        """Create a safe filename from a URL."""

        parsed = urlparse(url)

        name = parsed.path.strip("/") or "homepage"

        if parsed.query:
            name += "_" + parsed.query

        name = re.sub(r"[^a-zA-Z0-9_-]", "_", name)
        name = name[:100]

        return f"{name}.png"

    async def explore(self):

        print("\nStarting multi-page exploration...")

        start_url = self.normalize_url(self.start_url)

        self.pending_urls.append((start_url, 0))

        while self.pending_urls and len(self.visited_urls) < self.max_pages:

            current_url, depth = self.pending_urls.popleft()

            if current_url in self.visited_urls:
                continue

            self.visited_urls.add(current_url)

            print("\n--------------------------------")
            print(f"Exploring page: {current_url}")
            print(f"Depth: {depth}")
            print("--------------------------------")

            try:

                response = await self.page.goto(
                    current_url,
                    wait_until="domcontentloaded",
                    timeout=60000
                )

                if response and response.status >= 400:

                    self.failed_pages.append({
                        "url": current_url,
                        "reason": f"HTTP {response.status}"
                    })

                    print(f"Page returned HTTP {response.status}")
                    continue

                # Inspect the current page
                result = await self.explorer.inspect_page()

                result["depth"] = depth

                # Save page screenshot
                screenshot_name = self.save_screenshot(current_url)

                screenshot_folder = (
                    Path(__file__).resolve().parents[3]
                    / "storage"
                    / "screenshots"
                    / "exploration"
                )

                screenshot_folder.mkdir(
                    parents=True,
                    exist_ok=True
                )

                screenshot_path = screenshot_folder / screenshot_name

                await self.page.screenshot(
                    path=str(screenshot_path),
                    full_page=True
                )

                result["screenshot"] = str(screenshot_path)

                self.page_results.append(result)

                print("Page inspection successful!")

                # Stop expanding when maximum depth is reached
                if depth >= self.max_depth:
                    continue

                # Discover new internal links
                discovered_links = await self.discover_links()

                for link in discovered_links:

                    if link not in self.visited_urls:

                        self.pending_urls.append(
                            (link, depth + 1)
                        )

                print(
                    f"New internal links discovered: "
                    f"{len(discovered_links)}"
                )

            except Exception as error:

                self.failed_pages.append({
                    "url": current_url,
                    "reason": str(error)
                })

                print(f"Failed to explore page: {error}")

        return self.generate_report()

    def generate_report(self):
        """Build the final application map."""

        report = {
            "exploration_time": datetime.now().isoformat(),

            "website": {
                "start_url": self.start_url,
                "domain": self.base_domain
            },

            "configuration": {
                "max_pages": self.max_pages,
                "max_depth": self.max_depth
            },

            "summary": {
                "pages_explored": len(self.page_results),
                "pages_failed": len(self.failed_pages),
                "pages_remaining": len(self.pending_urls)
            },

            "pages": self.page_results,

            "failed_pages": self.failed_pages,

            "pending_pages": [
                {"url": url, "depth": depth}
                for url, depth in self.pending_urls
            ]
        }

        return report

    def save_report(self, report):
        """Save complete application map as JSON."""

        project_root = Path(__file__).resolve().parents[3]

        output_folder = (
            project_root / "generated" / "application_maps"
        )

        output_folder.mkdir(
            parents=True,
            exist_ok=True
        )

        report_path = output_folder / "multi_page_exploration.json"

        with open(report_path, "w", encoding="utf-8") as file:

            json.dump(
                report,
                file,
                indent=4,
                ensure_ascii=False
            )

        print(f"\nApplication map saved: {report_path}")

    def display_summary(self, report):

        summary = report["summary"]

        print("\n========== WEBSITE EXPLORATION REPORT ==========")

        print(f"Website: {self.start_url}")
        print(f"Pages explored: {summary['pages_explored']}")
        print(f"Pages failed: {summary['pages_failed']}")
        print(f"Pages remaining: {summary['pages_remaining']}")

        print("\nDiscovered pages:")

        for index, result in enumerate(report["pages"], start=1):

            print(
                f"{index}. "
                f"{result['website']['title']} "
                f"- {result['website']['url']}"
            )

        print("================================================")


async def main():

    browser_manager = BrowserManager()

    try:

        # Launch browser
        page = await browser_manager.start_browser()

        # Create multi-page explorer
        explorer = MultiPageExplorer(
            page=page,
            start_url="https://demo.playwright.dev/todomvc/",
            max_pages=20,
            max_depth=3
        )

        # Explore website
        report = await explorer.explore()

        # Display results
        explorer.display_summary(report)

        # Save application map
        explorer.save_report(report)

    except Exception as error:

        print(f"Exploration error: {error}")

    finally:

        await browser_manager.close_browser()


if __name__ == "__main__":

    asyncio.run(main())
