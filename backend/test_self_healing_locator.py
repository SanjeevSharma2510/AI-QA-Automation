
import asyncio

from playwright.async_api import async_playwright

from app.execution.self_healing_locator import (
    resolve_self_healing_locator
)


async def main():

    async with async_playwright() as playwright:

        browser = await playwright.chromium.launch(
            headless=True
        )

        page = await browser.new_page()

        # Use local HTML so this test does not depend on an
        # external website.
        await page.set_content("""
            <html>
                <body>
                    <input
                        placeholder="What needs to be done?"
                    />
                </body>
            </html>
        """)

        locator = await resolve_self_healing_locator(
            page=page,
            test_case_id="TC-SELF-HEAL-001",
            element_name="todo_input",
            candidates=[
                {
                    "strategy": "getByPlaceholder",
                    "value": "Incorrect placeholder",
                    "options": {"exact": True}
                },
                {
                    "strategy": "getByPlaceholder",
                    "value": "What needs to be done?",
                    "options": {"exact": True}
                }
            ]
        )

        assert await locator.is_visible()

        actual_placeholder = await locator.get_attribute(
            "placeholder"
        )

        assert actual_placeholder == "What needs to be done?"

        print("Self-healing locator test passed!")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
