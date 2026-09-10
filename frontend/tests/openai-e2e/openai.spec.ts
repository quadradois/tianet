import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

async function enter(page: Page, mode: string) {
  await page.goto("/login");
  await page.getByRole("textbox", { name: "E-mail" }).fill(`operador+${mode}@example.test`);
  await page.getByLabel("Senha").fill("segredo-openai");
  await page.getByRole("button", { name: "Entrar" }).click();
  await expect(page).toHaveURL(/\/app(?:\?|$)/);
  await page.goto("/app/openai");
  await expect(page.getByRole("heading", { name: "Conexão OpenAI" })).toBeVisible();
  await expect(page).toHaveTitle("Conexão OpenAI | TiaNet");
  await expect(page.getByRole("link", { name: /OpenAI (conectado|não conectado)/ })).toHaveAttribute("href", "/app/openai");
  await expect(page.getByRole("navigation").getByText("OpenAI", { exact: true })).toHaveCount(0);
}

test("login fake mostra host oficial, código e detecta conexão pelo polling", async ({ page }) => {
  await enter(page, "desconectado");
  const main = page.locator("#conteudo-principal");
  await main.getByRole("button", { name: "Conectar conta OpenAI" }).click();
  const official = main.getByRole("link", { name: "Abrir login oficial da OpenAI" });
  await expect(official).toHaveAttribute("href", "https://auth.openai.com/codex/device");
  await expect(official).toHaveAttribute("rel", /noopener/);
  await expect(main.getByText("ABCD-EFGH")).toBeVisible();
  await expect(main.getByText("Conectado", { exact: true })).toBeVisible({ timeout: 15_000 });
});

test("diagnóstico é explícito e logout informa e remove somente a sessão local", async ({ page }) => {
  await enter(page, "conectado");
  const main = page.locator("#conteudo-principal");
  await expect(main.getByText("GPT Test")).toHaveCount(0);
  await main.getByRole("button", { name: "Atualizar diagnóstico" }).click();
  await expect(main.getByText("GPT Test (padrão)")).toBeVisible();
  await expect(main.getByRole("button", { name: /Diagnóstico disponível/ })).toBeDisabled();
  await expect(main.getByText(/interface não confirma revogação remota/i)).toBeVisible();
  await main.getByRole("button", { name: "Desconectar deste ambiente" }).click();
  await expect(main.getByText("Desconectado", { exact: true })).toBeVisible();
});

test("tela funciona por teclado, sem overflow e sem violação séria", async ({ page }) => {
  await enter(page, "desconectado");
  await page.keyboard.press("Tab");
  await expect(page.getByRole("link", { name: "Pular para o conteudo" })).toBeFocused();
  expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(0);
  const results = await new AxeBuilder({ page }).analyze();
  expect(results.violations.filter((item) => item.impact === "critical" || item.impact === "serious")).toEqual([]);
  expect(results.incomplete.filter((item) => item.id === "color-contrast")).toEqual([]);
});
