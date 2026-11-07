import { test, expect } from "@playwright/test";

import {
    resolveSelfHealingLocator
} from "../utils/self_healing_locator.js";

test(
    "Self-healing locator uses a valid alternative when the original fails",
    async ({ page }) => {

        await page.goto(
            "https://demo.playwright.dev/todomvc/#/"
        );

        const todoInput = await resolveSelfHealingLocator({
            page,
            testCaseId: "TC-SELF-HEAL-001",
            elementName: "todo_input",

            candidates: [
                {
                    strategy: "getByPlaceholder",
                    value: "Incorrect placeholder",
                    options: { exact: true }
                },
                {
                    strategy: "getByPlaceholder",
                    value: "What needs to be done?",
                    options: { exact: true }
                }
            ]
        });

        await expect(todoInput).toBeVisible();

        await expect(todoInput).toHaveAttribute(
            "placeholder",
            "What needs to be done?"
        );
    }
);