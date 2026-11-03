
import { test, expect } from "@playwright/test";
import { TodomvcPage } from "../pages/todomvc_page.js";

test(
    "TC-001: Validate initial rendering and attributes of TodoMVC input field",
    async ({ page }) => {

        // Step 1: Open the application.
        await page.goto(
            "https://demo.playwright.dev/todomvc/#/"
        );

        // Step 2: Create the page object.
        const todoPage = new TodomvcPage(page);

        // Step 3: Verify the input field is visible.
        await todoPage.expect_todo_input_visible();

        // Step 4: Verify the placeholder.
        await expect(todoPage.todo_input).toHaveAttribute(
            "placeholder",
            "What needs to be done?"
        );

        // Step 5: Verify the input is enabled.
        await expect(todoPage.todo_input).toBeEnabled();

        // Step 6: Verify the input is not readonly.
        await expect(todoPage.todo_input).not.toHaveAttribute(
            "readonly"
        );

        // Step 7: Verify the input is initially empty.
        await expect(todoPage.todo_input).toHaveValue("");

    }
);
