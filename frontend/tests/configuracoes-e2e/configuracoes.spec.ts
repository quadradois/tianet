import { resolve } from "node:path";

import { expect, test, type Page } from "@playwright/test";

function emailForInstitution(institution: string): string {
  const mode = institution.toLowerCase();
  return mode === "acme" ? "operador@example.test" : `operador+${mode}@example.test`;
}
async function login(page: Page, institution = "ACME") {
  await page.context().clearCookies();
  await page.goto("/login", { waitUntil: "domcontentloaded" });
  await page.getByRole("textbox", { name: "E-mail" }).fill(emailForInstitution(institution));
  await page.getByLabel("Senha").fill("segredo-configuracoes");
  await page.getByRole("button", { name: "Entrar" }).click();
  await expect(page).toHaveURL(/\/app(?:\?|$)/);
}

async function gotoConfiguracoes(page: Page) {
  await page.goto("/app/configuracoes-financeiras?modalidade=consignado&data_referencia=2026-08-14");
  await expect(page.getByRole("heading", { exact: true, name: "Configuracoes Financeiras" })).toBeVisible();
}

async function screenshotEvidence(page: Page, suffix: string) {
  await page.evaluate(() => {
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    const texts: Text[] = [];
    while (walker.nextNode()) texts.push(walker.currentNode as Text);
    for (const text of texts) text.data = text.data.replace(/Correlation ID: [A-Za-z0-9._:-]+/g, "Correlation ID: corr-evidence-298");
  });
  await page.screenshot({
    animations: "disabled",
    caret: "initial",
    fullPage: false,
    path: resolve(`../docs/audits/evidence/frontend-mvp-imp-298-${suffix}.png`),
  });
}

test("renderiza Configuracoes Financeiras oficiais e captura desktop/mobile", async ({ page }, testInfo) => {
  const backendHits: string[] = [];
  page.on("request", (request) => {
    if (request.url().includes("127.0.0.1:3210/credit")) backendHits.push(request.url());
  });
  await login(page, "ACME");
  await gotoConfiguracoes(page);
  await expect(page.getByText("Consignado").first()).toBeVisible();
  await expect(page.getByRole("region", { name: "Configuracoes oficiais" })).toBeVisible();
  await expect(page.getByText(/sem-calculo-frontend/)).toBeVisible();
  expect(backendHits).toEqual([]);
  const suffix = testInfo.project.name.includes("mobile") ? "configuracoes-mobile" : "configuracoes-desktop";
  await screenshotEvidence(page, suffix);
});

test("executa comandos governados sem expor token ao browser", async ({ page }) => {
  await login(page, "ACME");
  await gotoConfiguracoes(page);
  await page.locator('input[name="modalidade_codigo"]').fill("consignado");
  await page.locator('input[name="modalidade_nome"]').fill("Consignado");
  await page.getByRole("button", { name: "Criar modalidade" }).click();
  await expect(page.getByText(/Modalidade financeira cadastrada/)).toBeVisible();
  await page.locator('input[name="calendario_codigo"]').fill("br");
  await page.locator('input[name="calendario_nome"]').fill("Brasil");
  await page.getByRole("button", { name: "Criar calendario" }).click();
  await expect(page.getByText(/Calendario financeiro cadastrado/)).toBeVisible();
  await page.locator('input[name="config_modalidade"]').fill("consignado");
  await page.locator('input[name="config_calendario_id"]').fill("00000000-0000-4000-8000-000000000101");
  await page.locator('input[name="vigencia_inicio"]').fill("2026-08-14");
  await page.getByRole("button", { name: "Criar configuracao" }).click();
  await expect(page.getByText(/Configuracao financeira criada/)).toBeVisible();
  const firstId = "00000000-0000-4000-8000-000000000100";
  const ids = page.locator('input[name="configuracao_id"]');
  await ids.nth(0).fill(firstId);
  await ids.nth(1).fill(firstId);
  await ids.nth(2).fill(firstId);
  await ids.nth(3).fill(firstId);
  await ids.nth(4).fill(firstId);
  await page.locator('input[name="data_ativacao"]').fill("2026-08-20");
  await page.getByRole("button", { name: "Aprovar" }).click();
  await expect(page.getByText(/Configuracao financeira aprovada/)).toBeVisible();
  await page.getByRole("button", { name: "Programar" }).click();
  await expect(page.getByText(/Configuracao financeira programada/)).toBeVisible();
  await page.getByRole("button", { exact: true, name: "Ativar" }).click();
  await expect(page.getByText(/Configuracao financeira ativada/)).toBeVisible();
  await page.getByRole("button", { name: "Inativar" }).click();
  await expect(page.getByText(/Configuracao financeira inativada/)).toBeVisible();
  await page.getByRole("button", { name: "Capturar snapshot" }).click();
  await expect(page.getByText(/Snapshot contratual capturado/)).toBeVisible();
  await expect(page.getByText(/access-|refresh-|Bearer/)).toHaveCount(0);
});

test("observa denied, empty, 404, 422 e 5xx seguros", async ({ page }, testInfo) => {
  await login(page, "nenhuma");
  await gotoConfiguracoes(page);
  await expect(page.getByText("Sem permissao").first()).toBeVisible();
  await login(page, "vazio");
  await gotoConfiguracoes(page);
  await expect(page.getByText(/Nenhuma configuracao financeira encontrada/)).toBeVisible();
  await login(page, "nao-encontrado");
  await gotoConfiguracoes(page);
  await expect(page.getByRole("alert").first()).toContainText("Configuracao Financeira nao encontrada ou indisponivel.");
  await expect(page.getByText("detalhe cross tenant")).toHaveCount(0);
  await login(page, "regra");
  await gotoConfiguracoes(page);
  await page.locator('input[name="modalidade_codigo"]').fill("consignado");
  await page.locator('input[name="modalidade_nome"]').fill("Consignado");
  await page.getByRole("button", { name: "Criar modalidade" }).click();
  await expect(page.getByText(/Regra de Configuracoes Financeiras rejeitou/)).toBeVisible();
  await expect(page.getByText("detalhe financeiro interno")).toHaveCount(0);
  await login(page, "estados");
  await gotoConfiguracoes(page);
  const serviceAlert = page.getByRole("alert").first();
  await expect(serviceAlert).toContainText("Servico temporariamente indisponivel.");
  await expect(page.getByText("stack secreta")).toHaveCount(0);
  await serviceAlert.scrollIntoViewIfNeeded();
  if (testInfo.project.name.includes("desktop")) await screenshotEvidence(page, "configuracoes-states-desktop");
  if (testInfo.project.name.includes("mobile")) await screenshotEvidence(page, "configuracoes-states-mobile");
});
