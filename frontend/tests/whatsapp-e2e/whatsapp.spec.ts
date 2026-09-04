import { resolve } from "node:path";

import { expect, test, type Page } from "@playwright/test";

async function login(page: Page, modo: string) {
  await page.goto("/login");
  await page.getByRole("textbox", { name: "E-mail" }).fill(`operador+${modo}@example.test`);
  await page.getByLabel("Senha").fill("segredo-whatsapp");
  await page.getByRole("button", { name: "Entrar" }).click();
  await expect(page).toHaveURL(/\/app(?:\?|$)/);
}

async function abrirConexao(page: Page) {
  await page.goto("/app/whatsapp");
  await expect(page.getByRole("heading", { name: "Conexao do WhatsApp" })).toBeVisible();
}

/**
 * A TELA, sem o selo da barra lateral.
 *
 * Os dois dizem a mesma coisa de proposito — o selo avisa, a tela age — e um
 * localizador de pagina inteira pega os dois. Escopar ao conteudo principal e o
 * que separa "a tela mostra" de "algo na pagina mostra".
 */
function tela(page: Page) {
  return page.locator("#conteudo-principal");
}

test("sem instancia: oferece conectar, e o QR so aparece depois do clique", async ({ page }, testInfo) => {
  await login(page, "ausente");
  await abrirConexao(page);

  // O estado vai no TEXTO, nao so na cor — criterio de a11y do IMP-369.
  await expect(tela(page).getByText("Nao conectado")).toBeVisible();
  await expect(tela(page).getByText("Nenhuma instancia de WhatsApp foi criada ainda.")).toBeVisible();

  // ANTES do clique nao ha QR. Se ele aparecesse aqui, o `GET` estaria
  // devolvendo credencial de pareamento — o defeito que o IMP-368 corrigiu.
  await expect(tela(page).getByRole("img", { name: /QR code/i })).toHaveCount(0);

  const suffix = testInfo.project.name.includes("mobile") ? "whatsapp-ausente-mobile" : "whatsapp-ausente-desktop";
  await page.screenshot({ animations: "disabled", caret: "initial", fullPage: false, path: resolve(`../docs/audits/evidence/frontend-mvp-imp-369-${suffix}.png`) });

  await tela(page).getByRole("button", { name: "Conectar WhatsApp" }).click();
  await expect(tela(page).getByRole("img", { name: /QR code/i })).toBeVisible();
  await expect(tela(page).getByRole("button", { name: "Gerar novo QR" })).toBeVisible();

  const qrSuffix = testInfo.project.name.includes("mobile") ? "whatsapp-qr-mobile" : "whatsapp-qr-desktop";
  await page.screenshot({ animations: "disabled", caret: "initial", fullPage: false, path: resolve(`../docs/audits/evidence/frontend-mvp-imp-369-${qrSuffix}.png`) });
});

test("pareada: mostra telefone e nome como coisas diferentes", async ({ page }, testInfo) => {
  await login(page, "pareada");
  await abrirConexao(page);

  await expect(tela(page).getByText("Conectado", { exact: true })).toBeVisible();
  // Numero e push name sao CAMPOS DIFERENTES. Rotular um como o outro foi
  // defeito real, pego em review no IMP-367.
  await expect(tela(page).getByText("556299999999")).toBeVisible();
  await expect(tela(page).getByText("Barbosa")).toBeVisible();
  await expect(tela(page).getByRole("button", { name: "Desconectar" })).toBeVisible();

  const suffix = testInfo.project.name.includes("mobile") ? "whatsapp-pareada-mobile" : "whatsapp-pareada-desktop";
  await page.screenshot({ animations: "disabled", caret: "initial", fullPage: false, path: resolve(`../docs/audits/evidence/frontend-mvp-imp-369-${suffix}.png`) });
});

test("o selo da barra lateral acompanha o estado da conexao", async ({ page }) => {
  await login(page, "pareada");
  await page.goto("/app/whatsapp");
  await expect(page.getByRole("link", { name: /WhatsApp conectado/ })).toBeVisible();

  await login(page, "ausente");
  await page.goto("/app/whatsapp");
  await expect(page.getByRole("link", { name: /WhatsApp nao conectado/ })).toBeVisible();
});

test("quem so tem `ler` ve o estado e nao recebe acao de conectar", async ({ page }) => {
  await login(page, "soleitura");
  await abrirConexao(page);

  await expect(tela(page).getByText("Nao conectado")).toBeVisible();
  await expect(tela(page).getByRole("button", { name: "Conectar WhatsApp" })).toHaveCount(0);
  await expect(tela(page).getByText("Seu acesso permite ver o estado, mas nao conectar.")).toBeVisible();
});
