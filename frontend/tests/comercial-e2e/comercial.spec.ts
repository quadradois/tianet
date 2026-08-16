import { resolve } from "node:path";

import { expect, test, type BrowserContext, type Page } from "@playwright/test";

const IDS = {
  debtor: "00000000-0000-4000-8000-000000000010",
  proposal: "00000000-0000-4000-8000-000000000020",
  simulation: "00000000-0000-4000-8000-000000000021",
};

async function login(page: Page, institution = "ACME") {
  await page.goto("/login");
  await page.getByRole("textbox", { name: "Instituicao" }).fill(institution);
  await page.getByRole("textbox", { name: "E-mail" }).fill("operador@example.test");
  await page.getByLabel("Senha").fill("segredo-comercial");
  await page.getByRole("button", { name: "Entrar" }).click();
  await expect(page).toHaveURL(/\/app(?:\?|$)/);
}

async function assertNoToken(page: Page, context: BrowserContext) {
  expect(await page.content()).not.toMatch(/access-(?:acme|leitura|nenhuma|estados|aprovada)|refresh-/i);
  expect(await page.evaluate(() => ({ local: localStorage.length, session: sessionStorage.length }))).toEqual({ local: 0, session: 0 });
  expect((await context.cookies()).every((cookie) => cookie.httpOnly)).toBe(true);
}

async function prepareEvidenceScreenshot(page: Page) {
  await page.evaluate(() => {
    if (document.activeElement instanceof HTMLElement) document.activeElement.blur();
    const previous = document.querySelector("[data-evidence-stabilizer='comercial']");
    previous?.remove();
    const style = document.createElement("style");
    style.dataset.evidenceStabilizer = "comercial";
    style.textContent = "[aria-live='polite'] { visibility: hidden !important; }";
    document.head.appendChild(style);
    window.scrollTo(0, 0);
  });
}

test.beforeEach(async ({ page }) => {
  page.on("console", (message) => { if (message.type() === "error") throw new Error(`console error: ${message.text()}`); });
  page.on("pageerror", (error) => { throw error; });
});

test("parte de Devedor ativo, lista Comercial e nao envia Tenant ou Carteira do browser", async ({ page, context }, testInfo) => {
  const requests: string[] = [];
  page.on("request", (request) => requests.push(request.url()));
  await login(page);
  await page.goto(`/app/devedores/${IDS.debtor}`);
  await expect(page.getByRole("link", { name: "Abrir Comercial deste Devedor" })).toBeVisible();
  await page.getByRole("link", { name: "Abrir Comercial deste Devedor" }).click();
  await expect(page).toHaveURL(new RegExp(`/app/devedores/${IDS.debtor}/comercial$`));
  await expect(page.getByRole("heading", { name: "Simulacoes e propostas" })).toBeVisible();
  await expect(page.getByText("Jornada P0 a partir de Devedor ativo")).toBeVisible();
  await expect(page.getByText("empty")).toHaveCount(0);
  await expect(page.getByRole("region", { name: "Tabela de propostas comerciais com overflow" })).toBeVisible();
  await assertNoToken(page, context);
  expect(requests.every((url) => new URL(url).origin === "http://127.0.0.1:3104")).toBe(true);
  expect(requests.some((url) => url.includes("carteira_id=hostil") || url.includes("tenant_id=hostil"))).toBe(false);
  const suffix = testInfo.project.name.startsWith("mobile") ? "comercial-list-mobile" : "comercial-list-desktop";
  await prepareEvidenceScreenshot(page);
  await page.screenshot({ animations: "disabled", caret: "initial", fullPage: false, path: resolve(`../docs/audits/evidence/frontend-mvp-imp-292-${suffix}.png`) });
});

test("cria simulacao, cria proposta e aprova sem criar Contrato futuro", async ({ page, context }, testInfo) => {
  await login(page);
  await page.goto(`/app/devedores/${IDS.debtor}/comercial?tenant_id=hostil&carteira_id=hostil`);
  await page.locator("#simulation-parametros").fill('{"produto":"assistido","canal":"e2e"}');
  await expect(page.locator("#simulation-parametros")).toHaveValue('{"produto":"assistido","canal":"e2e"}');
  await page.getByRole("button", { name: "Criar simulacao comercial" }).click();
  await expect(page.getByText(/Simulacao comercial registrada/)).toBeVisible();
  await page.getByLabel("Simulacao vinculada opcional").fill(IDS.simulation);
  await page.locator("#proposal-parametros").fill('{"produto":"assistido","canal":"e2e"}');
  await page.getByRole("button", { name: "Criar proposta comercial" }).click();
  await expect(page.getByText(/Proposta comercial criada/)).toBeVisible();
  await page.goto(`/app/comercial/propostas/${IDS.proposal}`);
  await expect(page.getByRole("heading", { name: "Proposta comercial" })).toBeVisible();
  await page.getByRole("button", { name: "Aprovar proposta" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Aprovar proposta" }).click();
  await expect(page.getByText(/Decisao comercial registrada/)).toBeVisible();
  await expect(page.getByText(/criar contrato|assinar contrato|liberar credito/i)).toHaveCount(0);
  await assertNoToken(page, context);
  const suffix = testInfo.project.name.startsWith("mobile") ? "proposta-flow-mobile" : "proposta-detail-desktop";
  await prepareEvidenceScreenshot(page);
  await page.screenshot({ animations: "disabled", caret: "initial", fullPage: false, path: resolve(`../docs/audits/evidence/frontend-mvp-imp-292-${suffix}.png`) });
});

test("RBAC leitura, empty, 404, 409 e 422 permanecem seguros e correlacionados", async ({ page }) => {
  await login(page, "LEITURA");
  await page.goto(`/app/devedores/${IDS.debtor}/comercial`);
  await expect(page.getByText("Sem permissao para criar simulacao comercial.")).toBeVisible();
  await expect(page.getByText("Sem permissao para criar proposta comercial.")).toBeVisible();
  await page.goto(`/app/comercial/propostas/${IDS.proposal}`);
  await expect(page.getByText("Nenhuma decisao comercial disponivel.")).toBeVisible();
  await page.getByRole("button", { name: "Sair" }).click();
  await expect(page).toHaveURL(/\/login$/);
  await login(page, "VAZIO");
  await page.goto(`/app/devedores/${IDS.debtor}/comercial`);
  await expect(page.getByText(/empty/)).toBeVisible();
  await page.getByRole("button", { name: "Sair" }).click();
  await expect(page).toHaveURL(/\/login$/);
  await login(page, "NAO-ENCONTRADO");
  await page.goto(`/app/comercial/propostas/${IDS.proposal}`);
  await expect(page.getByRole("alert").filter({ hasText: "Recurso comercial nao encontrado ou indisponivel." })).toBeVisible();
  await expect(page.getByText(/cross-carteira/)).toHaveCount(0);
  await page.getByRole("button", { name: "Sair" }).click();
  await expect(page).toHaveURL(/\/login$/);
  await login(page);
  await page.goto(`/app/comercial/propostas/${IDS.proposal}`);
  await page.getByRole("button", { name: "Cancelar proposta" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Cancelar proposta" }).click();
  await expect(page.getByText(/Nao foi possivel concluir a operacao Comercial\. Correlation ID:/)).toBeVisible();
  await page.getByRole("dialog").getByRole("button", { exact: true, name: "Fechar" }).click();
  await page.getByRole("button", { name: "Expirar proposta" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Expirar proposta" }).click();
  await expect(page.getByText(/Nao foi possivel concluir a operacao Comercial\. Correlation ID:/)).toBeVisible();
});

test("falhas 5xx e overflow visual nao vazam detalhe interno", async ({ page }) => {
  await login(page, "ESTADOS");
  await page.goto(`/app/devedores/${IDS.debtor}/comercial`);
  await expect(page.getByText(/Correlation ID: corr-comercial-states-292/)).toBeVisible();
  await expect(page.getByText(/stack secreta/)).toHaveCount(0);
  await expect(page.getByText("Erro 500")).toBeVisible();
  await expect(page.getByRole("region", { name: "Tabela de propostas comerciais com overflow" })).toHaveCount(0);
});
