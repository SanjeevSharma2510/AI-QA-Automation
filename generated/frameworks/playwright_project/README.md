# AI Generated Playwright Framework

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
