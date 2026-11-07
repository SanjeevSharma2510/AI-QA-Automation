# Generic AI Action-Plan Playwright Framework

This standalone framework executes approved AI-generated
Playwright action plans using Python and pytest.

## Requirements

- Python 3.10+
- pip

## Setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium
```

## Run tests

```powershell
python -m pytest
```

## Output

- HTML report: artifacts/report.html
- Failure screenshots: artifacts/

## Supported actions

- navigate
- fill
- click
- press
- select
- assert_visible
- assert_text
- assert_attribute
- assert_value
- assert_count

## Supported locator strategies

- id
- css
- xpath
- text
- placeholder
- role
- label

## Important

This project executes JSON action plans and does not require
Gemini or the original AI QA application at runtime.

Review test plans before running against sensitive systems.
Do not place passwords, API keys, or other secrets directly
inside action-plan JSON files.
