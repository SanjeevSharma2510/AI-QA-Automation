import fs from "node:fs/promises";
import path from "node:path";

/**
 * Build a Playwright locator from an explicit locator definition.
 */
function buildLocator(page, definition) {
    const { strategy, value, options = {}, role } = definition;

    switch (strategy) {
        case "getByPlaceholder":
            return page.getByPlaceholder(value, options);

        case "getByLabel":
            return page.getByLabel(value, options);

        case "getByTestId":
            return page.getByTestId(value);

        case "getByRole":
            return page.getByRole(role || "button", {
                ...options,
                name: value
            });

        case "css":
            return page.locator(value);

        default:
            throw new Error(`Unsupported locator strategy: ${strategy}`);
    }
}

/**
 * Write one audit entry for every locator resolution.
 */
async function writeAudit(entry) {
    const auditDirectory = path.resolve("test-results");
    const auditFile = path.join(
        auditDirectory,
        "self-healing-audit.jsonl"
    );

    await fs.mkdir(auditDirectory, { recursive: true });

    await fs.appendFile(
        auditFile,
        JSON.stringify({
            timestamp: new Date().toISOString(),
            ...entry
        }) + "\n",
        "utf-8"
    );
}

/**
 * Resolve the original locator or use a safe alternative.
 *
 * A locator is accepted only if it matches exactly one
 * visible element.
 */
export async function resolveSelfHealingLocator({
    page,
    testCaseId,
    elementName,
    candidates
}) {
    if (!Array.isArray(candidates) || candidates.length === 0) {
        throw new Error("At least one locator candidate is required.");
    }

    const original = candidates[0];
    const failures = [];

    for (let index = 0; index < candidates.length; index++) {
        const candidate = candidates[index];

        try {
            const locator = buildLocator(page, candidate);
            const count = await locator.count();

            if (count !== 1) {
                failures.push({
                    strategy: candidate.strategy,
                    value: candidate.value,
                    reason: `Expected exactly one match, found ${count}`
                });

                continue;
            }

            const visible = await locator.isVisible();

            if (!visible) {
                failures.push({
                    strategy: candidate.strategy,
                    value: candidate.value,
                    reason: "Matched element is not visible"
                });

                continue;
            }

            const healed = index > 0;

            await writeAudit({
                testCaseId,
                elementName,
                status: healed ? "HEALED" : "ORIGINAL_LOCATOR_WORKED",
                originalLocator: original,
                selectedLocator: candidate,
                failedCandidates: failures
            });

            if (healed) {
                console.log(
                    `[SELF-HEALING] ${testCaseId} - ${elementName}: ` +
                    `${original.strategy} replaced with ${candidate.strategy}`
                );
            }

            return locator;

        } catch (error) {
            failures.push({
                strategy: candidate.strategy,
                value: candidate.value,
                reason: error.message
            });
        }
    }

    await writeAudit({
        testCaseId,
        elementName,
        status: "HEALING_FAILED",
        originalLocator: original,
        selectedLocator: null,
        failedCandidates: failures
    });

    throw new Error(
        `Unable to resolve locator for ${elementName}. ` +
        `Checked ${candidates.length} candidates.`
    );
}