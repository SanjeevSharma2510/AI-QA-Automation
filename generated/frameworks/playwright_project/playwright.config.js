import { defineConfig, devices } from "@playwright/test";

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
    [
        "html",
        {
            outputFolder: "playwright-report",
            open: "never"
        }
    ],
    [
        "json",
        {
            outputFile: "playwright-report.json"
        }
    ]
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
