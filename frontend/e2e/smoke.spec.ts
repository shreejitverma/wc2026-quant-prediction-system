/**
 * Critical-path smoke (Phase 6 hardening):
 *  1. mode banner tells the truth (PAPER, from the backend - never hardcoded);
 *  2. the opportunity board renders ranked rows behind its MOCK banner;
 *  3. the kill switch fires end-to-end: typed phrase -> ledgered command ->
 *     KILLED state everywhere. Runs on a scratch ledger; see playwright.config.
 */
import { expect, test } from "@playwright/test";

test("mode banner is PAPER and comes from the backend", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("● PAPER")).toBeVisible();
  await expect(page.getByText("● LIVE")).toHaveCount(0);
});

test("opportunity board renders ranked rows behind the MOCK banner", async ({ page }) => {
  await page.goto("/opportunities");
  await expect(page.getByText("MOCK DATA", { exact: false })).toBeVisible();
  const rows = page.locator("[data-testid^='opp-row-']");
  await expect(rows.first()).toBeVisible();
  expect(await rows.count()).toBeGreaterThan(3);
  // Quarantined rows exist and are marked.
  await expect(page.locator("[data-quarantined='true']").first()).toBeVisible();
});

test("kill switch fires end-to-end and the terminal shows KILLED", async ({ page }) => {
  await page.goto("/");
  // Confirm stays disabled until the exact phrase is typed.
  await page.getByRole("button", { name: "KILL", exact: true }).click();
  const confirm = page.getByRole("button", { name: "Kill", exact: true });
  await expect(confirm).toBeDisabled();
  await page.getByRole("textbox").last().fill("KILL ALL");
  await expect(confirm).toBeDisabled();
  await page.getByRole("textbox").last().fill("KILL ALL QUOTING");
  await expect(confirm).toBeEnabled();
  await confirm.click();
  // The strip flips to KILLED (health re-read from the ledger fold).
  await expect(page.getByText("● KILLED")).toBeVisible({ timeout: 10_000 });
  // And the command is in the ledger, visible on the Ledger page.
  await page.goto("/ledger");
  await expect(page.getByText("VALID", { exact: false }).first()).toBeVisible();
  await expect(page.getByText("kill_switch", { exact: false }).first()).toBeVisible();
});

test("matchday view renders read-mostly essentials", async ({ page }) => {
  await page.goto("/matchday");
  await expect(page.getByText("Today")).toBeVisible();
  await expect(page.getByText("Top edges", { exact: false })).toBeVisible();
});
