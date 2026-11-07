
from pathlib import Path

import pytest

from playwright.sync_api import sync_playwright


ARTIFACTS_DIR = (
    Path(__file__).parent
    / "artifacts"
)


@pytest.fixture
def page(request):

    ARTIFACTS_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    with sync_playwright() as playwright:

        browser = playwright.chromium.launch(
            headless=True
        )

        context = browser.new_context()

        browser_page = context.new_page()

        yield browser_page

        report = getattr(
            request.node,
            "rep_call",
            None
        )

        if report and report.failed:

            screenshot_path = (
                ARTIFACTS_DIR
                / f"{request.node.name}.png"
            )

            browser_page.screenshot(
                path=str(screenshot_path),
                full_page=True
            )

            print(
                f"Failure screenshot: {screenshot_path}"
            )

        context.close()
        browser.close()


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):

    outcome = yield

    report = outcome.get_result()

    setattr(
        item,
        "rep_" + report.when,
        report
    )
