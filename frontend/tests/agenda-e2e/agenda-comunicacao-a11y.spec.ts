import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

function emailForInstitution(institution: string): string {
  const mode = institution.toLowerCase();
  return mode === "acme" ? "operador@example.test" : `operador+${mode}@example.test`;
}
async function login(page: Page, institution = "ACME") {
  await page.goto("/login");
  await page.getByRole("textbox", { name: "E-mail" }).fill(emailForInstitution(institution));
  await page.getByLabel("Senha").fill("segredo-agenda");
  await page.getByRole("button", { name: "Entrar" }).click();
  await expect(page).toHaveURL(/\/app(?:\?|$)/);
}

test("Agenda/Comunicacao preserva axe e foco por teclado", async ({ page }) => {
  await login(page, "ACME");
  await page.goto("/app/agenda");
  await expect(page.getByRole("heading", { name: "Agenda e Comunicacao", exact: true })).toBeVisible();
  await page.keyboard.press("Tab");
  await page.keyboard.press("Tab");
  await expect(page.locator(":focus")).toBeVisible();
  const results = await new AxeBuilder({ page }).analyze();
  expect(results.violations).toEqual([]);
});
