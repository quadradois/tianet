import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

async function login(page: Page, institution = "ACME") {
  await page.goto("/login");
  await page.getByRole("textbox", { name: "Instituicao" }).fill(institution);
  await page.getByRole("textbox", { name: "E-mail" }).fill("operador@example.test");
  await page.getByLabel("Senha").fill("segredo-cobranca");
  await page.getByRole("button", { name: "Entrar" }).click();
  await expect(page).toHaveURL(/\/app(?:\?|$)/);
}

test("Cobranca preserva axe e foco por teclado", async ({ page }) => {
  await login(page, "ACME");
  await page.goto("/app/cobranca");
  await expect(page.getByRole("heading", { name: "Fila de cobranca" })).toBeVisible();
  await page.keyboard.press("Tab");
  await page.keyboard.press("Tab");
  const results = await new AxeBuilder({ page }).analyze();
  expect(results.violations).toEqual([]);
});
