import { expect, test } from "@playwright/test";

test("observa o placeholder governado na raiz", async ({ page }) => {
  const consoleErrors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });

  const response = await page.goto("/");

  expect(response?.ok()).toBe(true);
  await expect(page).toHaveTitle("TiaNet");
  await expect(page.getByRole("heading", { name: "TiaNet" })).toBeVisible();
  expect(consoleErrors).toEqual([]);
});
