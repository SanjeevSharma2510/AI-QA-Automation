# AI Generated Python Playwright Framework

This framework contains Python Playwright tests generated
from human-approved and successfully executed test cases.

## Requirements

- Python 3.10+
- pip

## 1. Create virtual environment

Windows:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## 2. Install dependencies

```bash
pip install -r requirements.txt
```

## 3. Install Chromium

```bash
playwright install chromium
```

## 4. Configure application URL

Copy `.env.example` to `.env`.

Update BASE_URL with your application URL.

Set HEADLESS=false to see the browser.

Note: Environment variables must be loaded by your shell
or your chosen environment loader before running pytest.

Windows PowerShell example:

```powershell
$env:BASE_URL="https://demo.playwright.dev/todomvc/#/"
$env:HEADLESS="false"
```

## 5. Run all tests

```bash
pytest
```

## 6. Run tests with visible browser

PowerShell:

```powershell
$env:HEADLESS="false"
pytest
```

## 7. HTML report

After execution, open:

```text
artifacts/report.html
```

## 8. Failure screenshots

Screenshots are saved under:

```text
artifacts/
```

## Project structure

- tests/: Generated pytest test scripts
- pages/: Page Object Model classes
- conftest.py: Browser fixtures
- pytest.ini: Pytest configuration
- requirements.txt: Dependencies
- artifacts/: Reports and failure screenshots

## Important

The generated framework does not require Gemini to execute.

Only human-approved test cases with passed execution
are included in this framework.

Review the generated test scripts before running them
against production or other sensitive environments.
