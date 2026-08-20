import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

test("Automacao passa por axe, teclado e overflow nos dois viewports", async ({ page }) => {
  page.on("console", (message) => { if (message.type() === "error") throw new Error(message.text()); });
  page.on("pageerror", (error) => { throw error; });
  await page.goto("/login");
  await page.getByRole("textbox", { name: "E-mail" }).fill("operador@example.test");
  await page.getByLabel("Senha").fill("segredo-automacao");
  await page.getByRole("button", { name: "Entrar" }).click();
  await expect(page).toHaveURL(/\/app(?:\?|$)/);
  await page.goto("/app/automacao?job_id=00000000-0000-4000-8000-000000000081&notification_id=00000000-0000-4000-8000-000000000082");
  await expect(page.getByRole("heading", { name: "Jobs, Templates e Notificacoes" })).toBeVisible();
  const results = await new AxeBuilder({ page }).disableRules(["color-contrast"]).analyze();
  expect(results.violations.filter((violation) => violation.impact === "critical" || violation.impact === "serious")).toEqual([]);
  await page.keyboard.press("Tab");
  await expect(page.getByRole("link", { name: "Pular para o conteudo" })).toBeFocused();
  await page.getByRole("button", { name: "Consultar Automacao" }).focus();
  await expect(page.getByRole("button", { name: "Consultar Automacao" })).toBeFocused();
  expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(0);
  await expect(page.getByRole("region", { name: "Jobs de Automacao com overflow" })).toBeVisible();
});
