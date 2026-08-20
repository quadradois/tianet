import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

test("IAM permitido passa por axe, teclado e overflow nos dois viewports", async ({ page }) => {
  page.on("console", (message) => { if (message.type() === "error") throw new Error(message.text()); });
  page.on("pageerror", (error) => { throw error; });
  await page.goto("/login");
  await page.getByRole("textbox", { name: "E-mail" }).fill("operador@example.test");
  await page.getByLabel("Senha").fill("segredo-iam");
  await page.getByRole("button", { name: "Entrar" }).click();
  await expect(page).toHaveURL(/\/app(?:\?|$)/);
  await page.goto("/app/iam?perfil_id=00000000-0000-4000-8000-000000000004&usuario_id=00000000-0000-4000-8000-000000000005");
  await expect(page.getByRole("heading", { name: "Perfis, catalogo e atribuicoes" })).toBeVisible();
  const results = await new AxeBuilder({ page }).disableRules(["color-contrast"]).analyze();
  expect(results.violations.filter((violation) => violation.impact === "critical" || violation.impact === "serious")).toEqual([]);
  await page.keyboard.press("Tab");
  await expect(page.getByRole("link", { name: "Pular para o conteudo" })).toBeFocused();
  await page.getByRole("button", { name: "Consultar IAM" }).focus();
  await expect(page.getByRole("button", { name: "Consultar IAM" })).toBeFocused();
  expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(0);
});
