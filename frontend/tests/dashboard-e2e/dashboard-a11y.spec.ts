import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

test("Dashboard passa por axe, teclado e overflow nos dois viewports", async ({ page }) => {
  page.on("console", (message) => { if (message.type() === "error") throw new Error(message.text()); });
  page.on("pageerror", (error) => { throw error; });
  await page.goto("/login");
  await page.getByRole("textbox", { name: "Instituicao" }).fill("ACME");
  await page.getByRole("textbox", { name: "E-mail" }).fill("operador@example.test");
  await page.getByLabel("Senha").fill("segredo-dashboard");
  await page.getByRole("button", { name: "Entrar" }).click();
  await expect(page.getByRole("heading", { name: "Inicio" })).toBeVisible();
  const results = await new AxeBuilder({ page }).analyze();
  expect(results.violations.filter((violation) => violation.impact === "critical" || violation.impact === "serious")).toEqual([]);
  expect(results.incomplete.filter((item) => item.id === "color-contrast")).toEqual([]);
  await page.reload();
  await expect(page.getByRole("heading", { name: "Inicio" })).toBeVisible();
  await page.keyboard.press("Tab");
  await expect(page.getByRole("link", { name: "Pular para o conteudo" })).toBeFocused();
  await page.getByRole("region", { name: "Fila de cobranca" }).focus();
  await expect(page.getByRole("region", { name: "Fila de cobranca" })).toBeFocused();
  expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(0);
});
