import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

test("Configuracoes Financeiras passa por axe, teclado e overflow nos dois viewports", async ({ page }) => {
  page.on("console", (message) => { if (message.type() === "error") throw new Error(message.text()); });
  page.on("pageerror", (error) => { throw error; });
  await page.goto("/login");
  await page.getByRole("textbox", { name: "E-mail" }).fill("operador+vazio@example.test");
  await page.getByLabel("Senha").fill("segredo-configuracoes");
  await page.getByRole("button", { name: "Entrar" }).click();
  await expect(page).toHaveURL(/\/app(?:\?|$)/);
  await page.goto("/app/configuracoes-financeiras?modalidade=consignado&data_referencia=2026-08-14");
  await expect(page.getByRole("heading", { name: "Configuracoes Financeiras", exact: true })).toBeVisible();
  await expect(page.getByText(/Nenhuma configuracao financeira encontrada/).first()).toBeVisible();
  const results = await new AxeBuilder({ page }).analyze();
  expect(results.violations.filter((violation) => violation.impact === "critical" || violation.impact === "serious")).toEqual([]);
  expect(results.incomplete.filter((item) => item.id === "color-contrast")).toEqual([]);
  await page.keyboard.press("Tab");
  await expect(page.getByRole("link", { name: "Pular para o conteudo" })).toBeFocused();
  await page.getByRole("button", { name: "Consultar" }).focus();
  await expect(page.getByRole("button", { name: "Consultar" })).toBeFocused();
  expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(0);
});
