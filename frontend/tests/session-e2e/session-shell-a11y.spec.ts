import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

async function expectNoSeriousViolations(page: Page) {
  const results = await new AxeBuilder({ page }).analyze();
  expect(results.violations.filter((violation) => violation.impact === "critical" || violation.impact === "serious")).toEqual([]);
  expect(results.incomplete.filter((item) => item.id === "color-contrast")).toEqual([]);
}

test("login e shell passam pelo gate axe e teclado", async ({ page }) => {
  await page.goto("/login");
  await expectNoSeriousViolations(page);
  await page.keyboard.press("Tab");
  await expect(page.getByRole("link", { name: "Pular para o conteudo" })).toBeFocused();
  await page.getByRole("textbox", { name: "E-mail" }).fill("operador@example.test");
  await page.getByLabel("Senha").fill("segredo-e2e");
  await page.getByRole("button", { name: "Entrar" }).click();
  await expect(page.getByText("Carteira Centro")).toBeVisible();
  await expect(page).toHaveTitle("Dashboard | TiaNet");
  await expectNoSeriousViolations(page);
  const viewport = page.viewportSize();
  if (viewport) {
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow).toBeLessThanOrEqual(0);
  }
});

test("banner de queda passa pelo gate axe e e operavel por teclado", async ({ page }) => {
  await page.goto("/login");
  await page.getByRole("textbox", { name: "E-mail" }).fill("operador+queda@example.test");
  await page.getByLabel("Senha").fill("segredo-e2e");
  await page.getByRole("button", { name: "Entrar" }).click();
  const banner = page.getByRole("alert").filter({ hasText: "Conexão do WhatsApp caiu" });
  await expect(banner).toBeVisible();
  await expectNoSeriousViolations(page);
  const link = page.getByRole("link", { name: "Abrir conexão do WhatsApp" });
  await link.focus();
  await expect(link).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\/app\/whatsapp$/);
  await expect(page.getByRole("alert").filter({ hasText: "Conexão do WhatsApp caiu" })).toBeVisible();
  await expectNoSeriousViolations(page);
  const viewport = page.viewportSize();
  if (viewport) {
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow).toBeLessThanOrEqual(0);
  }
});
