import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

async function entrar(page: Page, modo: string) {
  await page.goto("/login");
  await page.getByRole("textbox", { name: "E-mail" }).fill(`operador+${modo}@example.test`);
  await page.getByLabel("Senha").fill("segredo-pagamentos");
  await page.getByRole("button", { name: "Entrar" }).click();
  await expect(page).toHaveURL(/\/app(?:\?|$)/);
  await page.goto("/app/pagamentos");
}

test("a taxa fica visível e ligar exige credencial testada", async ({ page }) => {
  await entrar(page, "novo");
  const main = page.locator("#conteudo-principal");
  await expect(page.getByRole("heading", { level: 1, name: "Recebimento" })).toBeVisible();
  await expect(main.getByText(/0,99% por recebimento/)).toBeVisible();

  // Sem credencial: ligar e testar indisponíveis.
  await expect(main.getByRole("button", { name: "Ligar recebimento" })).toBeDisabled();
  await expect(main.getByRole("button", { name: "Testar credencial" })).toBeDisabled();

  await main.getByLabel("Access token de producao").fill("APP_USR-token-de-producao");
  await main.getByLabel("Segredo do webhook").fill("segredo-do-webhook");
  await main.getByRole("button", { name: "Salvar credenciais" }).click();
  await expect(main.getByTestId("mercadopago-estado")).toHaveText(/Teste antes de ligar/);
  // Credencial salva, mas ainda sem teste: ligar segue bloqueado.
  await expect(main.getByRole("button", { name: "Ligar recebimento" })).toBeDisabled();

  await main.getByRole("button", { name: "Testar credencial" }).click();
  await expect(main.getByText(/Credencial aceita pelo provedor/)).toBeVisible();
  await main.getByRole("button", { name: "Ligar recebimento" }).click();
  await expect(main.getByText(/Recebimento por Pix ligado/)).toBeVisible();
  await expect(main.getByRole("button", { name: "Desligar recebimento" })).toBeVisible();
});

test("desligar avisa que cobranças em aberto seguem valendo", async ({ page }) => {
  await entrar(page, "novo");
  const main = page.locator("#conteudo-principal");
  await main.getByLabel("Access token de producao").fill("APP_USR-token-de-producao");
  await main.getByLabel("Segredo do webhook").fill("segredo-do-webhook");
  await main.getByRole("button", { name: "Salvar credenciais" }).click();
  await main.getByRole("button", { name: "Testar credencial" }).click();
  await main.getByRole("button", { name: "Ligar recebimento" }).click();

  await main.getByRole("button", { name: "Desligar recebimento" }).click();

  await expect(main.getByText(/Cobrancas em aberto seguem valendo/)).toBeVisible();
  await expect(main.getByRole("button", { name: "Ligar recebimento" })).toBeEnabled();
});

test("sem a permissão a tela não oferece escrita nem link na navegação", async ({ page }) => {
  await entrar(page, "leitura");
  const main = page.locator("#conteudo-principal");

  await expect(main.getByRole("button", { name: "Ligar recebimento" })).toHaveCount(0);
  await expect(main.getByLabel("Access token de producao")).toHaveCount(0);
  await expect(page.getByRole("navigation").getByText("Recebimento", { exact: true })).toHaveCount(0);
});

test("tela funciona por teclado, sem overflow e sem violação séria", async ({ page }) => {
  await entrar(page, "novo");
  await page.keyboard.press("Tab");
  await expect(page.getByRole("link", { name: "Pular para o conteudo" })).toBeFocused();
  expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(0);
  const results = await new AxeBuilder({ page }).analyze();
  expect(results.violations.filter((item) => item.impact === "critical" || item.impact === "serious")).toEqual([]);
  expect(results.incomplete.filter((item) => item.id === "color-contrast")).toEqual([]);
});

test("a chave Pix sem taxa é cadastrada e passa a ser oferecida", async ({ page }) => {
  await entrar(page, "novo");
  const main = page.locator("#conteudo-principal");
  await expect(main.getByTestId("chave-pix-estado")).toHaveText(/nao oferece Pix ate cadastrar/i);

  await main.getByLabel("Chave", { exact: true }).fill("5562999998888");
  await main.getByLabel("Nome do favorecido").fill("Ivonete");
  await main.getByRole("button", { name: "Salvar chave" }).click();

  await expect(main.getByTestId("chave-pix-estado")).toContainText("5562999998888");
  await expect(main.getByTestId("chave-pix-estado")).toContainText("Ivonete");
});
