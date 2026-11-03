
import json
from pathlib import Path
from datetime import datetime, timezone


PROJECT_ROOT = Path(__file__).resolve().parents[3]

FRAMEWORK_DIR = (
    PROJECT_ROOT
    / "generated"
    / "frameworks"
    / "playwright_project"
)

TESTS_DIR = FRAMEWORK_DIR / "tests"
PAGES_DIR = FRAMEWORK_DIR / "pages"
TEST_DATA_DIR = FRAMEWORK_DIR / "test-data"


class PlaywrightProjectGenerator:

    def __init__(self):
        self.required_files = [
            TESTS_DIR / "TC-001.spec.js",
            PAGES_DIR / "todomvc_page.js",
            PAGES_DIR / "locators.js",
        ]

    def validate_generated_files(self):
        print("\nChecking generated automation files...")

        missing_files = []

        for file_path in self.required_files:
            if file_path.exists() and file_path.stat().st_size > 0:
                print(f"[OK] {file_path.relative_to(FRAMEWORK_DIR)}")
            else:
                print(f"[MISSING] {file_path}")
                missing_files.append(file_path)

        if missing_files:
            raise FileNotFoundError(
                "Some generated files are missing or empty. "
                "Complete the previous generation steps first."
            )

    def create_project_structure(self):
        print("\nCreating project folders...")

        TESTS_DIR.mkdir(parents=True, exist_ok=True)
        PAGES_DIR.mkdir(parents=True, exist_ok=True)
        TEST_DATA_DIR.mkdir(parents=True, exist_ok=True)

        print("[OK] tests/")
        print("[OK] pages/")
        print("[OK] test-data/")

    def create_package_json(self):
        package = {
            "name": "ai-generated-playwright-framework",
            "version": "1.0.0",
            "private": True,
            "description": (
                "Standalone Playwright automation framework "
                "generated from human-approved test cases."
            ),
            "scripts": {
                "test": "playwright test",
                "test:headed": "playwright test --headed",
                "test:debug": "playwright test --debug",
                "test:report": "playwright show-report"
            },
            "devDependencies": {
                "@playwright/test": "^1.55.0"
            }
        }

        output_file = FRAMEWORK_DIR / "package.json"

        output_file.write_text(
            json.dumps(package, indent=4),
            encoding="utf-8"
        )

        print(f"[OK] Created {output_file.name}")

    def create_playwright_config(self):
        config = r'''import { defineConfig, devices } from "@playwright/test";

export default defineConfig({

    // Location of generated test files.
    testDir: "./tests",

    // Run tests sequentially initially.
    fullyParallel: false,

    // Fail the build if test.only is accidentally committed.
    forbidOnly: Boolean(process.env.CI),

    // Retry failed tests in CI.
    retries: process.env.CI ? 2 : 0,

    // Use one worker initially for predictable execution.
    workers: process.env.CI ? 1 : undefined,

    // Test execution timeout.
    timeout: 30000,

    // Test reporters.
    reporter: [
        ["list"],
        ["html", { open: "never" }]
    ],

    use: {
        ...devices["Desktop Chrome"],

        // Capture useful debugging evidence.
        screenshot: "only-on-failure",
        trace: "retain-on-failure",
        video: "retain-on-failure",

        actionTimeout: 10000,
        navigationTimeout: 15000
    },

    projects: [
        {
            name: "chromium",
            use: {
                ...devices["Desktop Chrome"]
            }
        }
    ],

    outputDir: "./test-results"
});
'''

        output_file = FRAMEWORK_DIR / "playwright.config.js"

        output_file.write_text(
            config,
            encoding="utf-8"
        )

        print(f"[OK] Created {output_file.name}")

    def create_gitignore(self):
        content = """node_modules/
playwright-report/
test-results/
playwright/.cache/
.env
"""

        output_file = FRAMEWORK_DIR / ".gitignore"

        output_file.write_text(
            content,
            encoding="utf-8"
        )

        print("[OK] Created .gitignore")

    def create_readme(self):
        content = """# AI Generated Playwright Framework

This project contains Playwright automation scripts generated
from human-reviewed and approved test cases.

## Requirements

- Node.js
- npm

## Installation

Install project dependencies:

```bash
npm install
```

Install Chromium:

```bash
npx playwright install chromium
```

## Run all tests

```bash
npm test
```

## Run tests with a visible browser

```bash
npm run test:headed
```

## Debug tests

```bash
npm run test:debug
```

## Open HTML report

```bash
npm run test:report
```

## Project folders

- tests/: Generated Playwright test scripts
- pages/: Reusable Page Object Model classes
- test-data/: Test data files
- playwright.config.js: Playwright configuration

## AI dependency

Gemini is not required to execute generated tests.

The generated JavaScript tests execute directly through Playwright.
"""

        output_file = FRAMEWORK_DIR / "README.md"

        output_file.write_text(
            content,
            encoding="utf-8"
        )

        print("[OK] Created README.md")

    def create_manifest(self):
        manifest = {
            "generated_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "project_name": "AI Generated Playwright Framework",
            "framework": "Playwright",
            "language": "JavaScript",
            "ai_required_for_execution": False,
            "test_directory": "tests",
            "page_object_directory": "pages",
            "test_data_directory": "test-data",
            "browser": "chromium",
            "generation_status": "completed"
        }

        output_file = FRAMEWORK_DIR / "framework_manifest.json"

        output_file.write_text(
            json.dumps(manifest, indent=4),
            encoding="utf-8"
        )

        print("[OK] Created framework_manifest.json")

    def run(self):
        print("\n======================================")
        print(" PLAYWRIGHT PROJECT GENERATOR")
        print("======================================")

        FRAMEWORK_DIR.mkdir(parents=True, exist_ok=True)

        self.validate_generated_files()
        self.create_project_structure()
        self.create_package_json()
        self.create_playwright_config()
        self.create_gitignore()
        self.create_readme()
        self.create_manifest()

        print("\n======================================")
        print(" PROJECT GENERATION COMPLETED")
        print("======================================")
        print(f"Project location: {FRAMEWORK_DIR}")


if __name__ == "__main__":
    generator = PlaywrightProjectGenerator()
    generator.run()
