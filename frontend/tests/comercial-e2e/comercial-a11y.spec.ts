import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

const debtorId = "00000000-0000-4000-8000-000000000010";

async function login(page: Page) {
  await page.goto("/login");
  await page.getByRole("textbox", { name: "E-mail" }).fill("operador@example.test");
  await page.getByLabel("Senha").fill("segredo-comercial");
  await page.getByRole("button", { name: "Entrar" }).click();
  await expect(page).toHaveURL(/\/app(?:\?|$)/);
}

test("Comercial passa axe, teclado e overflow em desktop/mobile", async ({ page }) => {
  await login(page);
  await page.goto(`/app/devedores/${debtorId}/comercial`);
  const accessibility = await new AxeBuilder({ page }).analyze();
  expect(accessibility.violations.filter((violation) => ["critical", "serious"].includes(violation.impact ?? ""))).toEqual([]);
  await page.keyboard.press("Tab");
  await page.keyboard.press("Tab");
  await page.keyboard.press("Tab");
  await page.keyboard.press("Tab");
  await expect(page.getByRole("region", { name: "Tabela de propostas comerciais com overflow" })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(0);
});
