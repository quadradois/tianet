import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

async function entrar(page: Page, modo: string) {
  await page.goto("/login");
  await page.getByRole("textbox", { name: "E-mail" }).fill(`operador+${modo}@example.test`);
  await page.getByLabel("Senha").fill("segredo-whatsapp");
  await page.getByRole("button", { name: "Entrar" }).click();
  await expect(page).toHaveURL(/\/app(?:\?|$)/);
  await page.goto("/app/whatsapp");
  await expect(page.getByRole("heading", { name: "Conexao do WhatsApp" })).toBeVisible();
  // O `<title>` chega pela metadata do Next DEPOIS do conteudo. Sem esperar por
  // ele, o axe roda na janela em que o `<h1>` existe e o titulo nao — e reprova
  // com `document-title`. Mesmo padrao do dashboard e do session-shell.
  await expect(page).toHaveTitle("Conexao do WhatsApp | TiaNet");
}

async function semViolacaoSeria(page: Page) {
  const results = await new AxeBuilder({ page }).analyze();
  expect(results.violations.filter((violation) => violation.impact === "critical" || violation.impact === "serious")).toEqual([]);
  expect(results.incomplete.filter((item) => item.id === "color-contrast")).toEqual([]);
}

test("conexao ausente passa por axe, teclado e overflow", async ({ page }) => {
  page.on("console", (message) => { if (message.type() === "error") throw new Error(message.text()); });
  page.on("pageerror", (error) => { throw error; });

  await entrar(page, "ausente");
  await semViolacaoSeria(page);

  await page.keyboard.press("Tab");
  await expect(page.getByRole("link", { name: "Pular para o conteudo" })).toBeFocused();

  // O selo e um link de verdade, entao tem de ser alcancavel por teclado — e o
  // nome acessivel precisa dizer o ESTADO, nao so "WhatsApp": quem navega por
  // leitor de tela nao ve a bolinha colorida.
  await expect(page.getByRole("link", { name: /WhatsApp nao conectado/ })).toBeVisible();

  expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(0);
});

test("QR na tela nao introduz violacao, e a imagem tem texto alternativo", async ({ page }) => {
  page.on("pageerror", (error) => { throw error; });

  await entrar(page, "ausente");
  await page.locator("#conteudo-principal").getByRole("button", { name: "Conectar WhatsApp" }).click();
  await expect(page.locator("#conteudo-principal").getByRole("img", { name: /QR code/i })).toBeVisible();

  // O axe roda COM o QR na tela: imagem sem alternativa textual e violacao
  // seria, e o QR e o unico `<img>` desta tela.
  await semViolacaoSeria(page);
});

test("conexao pareada passa por axe", async ({ page }) => {
  page.on("pageerror", (error) => { throw error; });

  await entrar(page, "pareada");
  await semViolacaoSeria(page);
  await expect(page.getByRole("link", { name: /WhatsApp conectado/ })).toBeVisible();
});
