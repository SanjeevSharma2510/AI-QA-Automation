
import asyncio
from pathlib import Path

from playwright.async_api import async_playwright


class BrowserManager:

    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    async def start_browser(self):
        """Launch a visible Chromium browser."""

        print("Starting Chromium browser...")

        self.playwright = await async_playwright().start()

        self.browser = await self.playwright.chromium.launch(
            headless=False
        )

        self.context = await self.browser.new_context(
            viewport={"width": 1366, "height": 768}
        )

        self.page = await self.context.new_page()

        print("Browser launched successfully!")

        return self.page

    async def open_website(self, url):
        """Navigate to the requested website."""

        print(f"Opening website: {url}")

        await self.page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=60000
        )

        title = await self.page.title()
        current_url = self.page.url

        print(f"Website title: {title}")
        print(f"Current URL: {current_url}")

        return self.page

    async def take_screenshot(self, filename):
        """Capture a screenshot of the current page."""

        project_root = Path(__file__).resolve().parents[3]

        screenshot_folder = (
            project_root / "storage" / "screenshots"
        )

        screenshot_folder.mkdir(
            parents=True,
            exist_ok=True
        )

        screenshot_path = screenshot_folder / filename

        await self.page.screenshot(
            path=str(screenshot_path),
            full_page=True
        )

        print(f"Screenshot saved: {screenshot_path}")

    async def close_browser(self):
        """Close the browser and Playwright safely."""

        if self.browser:
            await self.browser.close()
            print("Browser closed.")

        if self.playwright:
            await self.playwright.stop()
            print("Playwright stopped.")


async def main():

    browser_manager = BrowserManager()

    try:
        # Step 1: Launch browser
        await browser_manager.start_browser()

        # Step 2: Open demo website
        await browser_manager.open_website(
            "https://demo.playwright.dev/todomvc/"
        )

        # Step 3: Take screenshot
        await browser_manager.take_screenshot(
            "demo_homepage.png"
        )

        # Step 4: Keep browser open for 5 seconds
        await asyncio.sleep(5)

    except Exception as error:
        print(f"An error occurred: {error}")

    finally:
        # Always close browser resources
        await browser_manager.close_browser()


if __name__ == "__main__":
    asyncio.run(main())
