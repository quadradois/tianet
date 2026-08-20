import { resolve } from "node:path";

import { expect, test, type BrowserContext, type Page } from "@playwright/test";

const IDS = {
  contract: "00000000-0000-4000-8000-000000000030",
  proposal: "00000000-0000-4000-8000-000000000020",
};

function emailForInstitution(institution: string): string {
  const mode = institution.toLowerCase();
  return mode === "acme" ? "operador@example.test" : `operador+${mode}@example.test`;
}
async function login(page: Page, institution = "ACME") {
  await page.goto("/login");
  await page.getByRole("textbox", { name: "E-mail" }).fill(emailForInstitution(institution));
  await page.getByLabel("Senha").fill("segredo-contratos");
  await page.getByRole("button", { name: "Entrar" }).click();
  await expect(page).toHaveURL(/\/app(?:\?|$)/);
}

async function assertNoToken(page: Page, context: BrowserContext) {
  expect(await page.content()).not.toMatch(/access-(?:acme|leitura|nenhuma|estados|assinado)|refresh-/i);
  expect(await page.evaluate(() => ({ local: localStorage.length, session: sessionStorage.length }))).toEqual({ local: 0, session: 0 });
  expect((await context.cookies()).every((cookie) => cookie.httpOnly)).toBe(true);
}

async function prepareEvidenceScreenshot(page: Page) {
  await page.evaluate(() => {
    if (document.activeElement instanceof HTMLElement) document.activeElement.blur();
    const previous = document.querySelector("[data-evidence-stabilizer='contratos']");
    previous?.remove();
    const style = document.createElement("style");
    style.dataset.evidenceStabilizer = "contratos";
    style.textContent = "[aria-live='polite'] { visibility: hidden !important; }";
    document.head.appendChild(style);
    window.scrollTo(0, 0);
  });
}

test.beforeEach(async ({ page }) => {
  page.on("console", (message) => { if (message.type() === "error") throw new Error(`console error: ${message.text()}`); });
  page.on("pageerror", (error) => { throw error; });
});

test("lista contratos e formaliza Proposta aprovada sem enviar Carteira do browser", async ({ page, context }, testInfo) => {
  const requests: string[] = [];
  page.on("request", (request) => requests.push(request.url()));
  await login(page);
  await page.goto(`/app/contratos?proposta_id=${IDS.proposal}&tenant_id=hostil&carteira_id=hostil`);
  await expect(page.getByRole("heading", { name: "Contratos de Credito" })).toBeVisible();
  // IMP-318 recolheu Contratos no grupo Administracao: o destino continua no
  // menu, mas so fica visivel com o grupo aberto.
  await page.locator("summary", { hasText: "Administracao" }).click();
  await expect(page.getByRole("link", { name: "Contratos" })).toHaveAttribute("href", "/app/contratos");
  await expect(page.getByRole("region", { name: "Tabela de contratos com overflow" })).toBeVisible();
  await expect(page.getByRole("textbox", { name: "Proposta aprovada" })).toHaveValue(IDS.proposal);
  await page.getByRole("button", { name: "Formalizar contrato" }).click();
  await expect(page.getByText(/Contrato formalizado a partir da Proposta aprovada/)).toBeVisible();
  await assertNoToken(page, context);
  expect(requests.every((url) => new URL(url).origin === "http://127.0.0.1:3105")).toBe(true);
  expect(requests.every((url) => !url.startsWith("http://127.0.0.1:3205"))).toBe(true);
  const suffix = testInfo.project.name.startsWith("mobile") ? "contratos-list-mobile" : "contratos-list-desktop";
  await prepareEvidenceScreenshot(page);
  await page.screenshot({ animations: "disabled", caret: "initial", fullPage: false, path: resolve(`../docs/audits/evidence/frontend-mvp-imp-293-${suffix}.png`) });
});

test("consulta detalhe, historico, assina e libera saida logica sem criar Motor", async ({ page, context }, testInfo) => {
  await login(page);
  await page.goto(`/app/contratos/${IDS.contract}`);
  await expect(page.getByRole("heading", { name: "Contrato de Credito" })).toBeVisible();
  await expect(page.getByText("Historico contratual")).toBeVisible();
  await page.getByRole("button", { name: "Assinar contrato" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Assinar contrato" }).click();
  await expect(page.getByText(/Acao contratual registrada/)).toBeVisible();
  await page.getByRole("dialog").getByRole("button", { exact: true, name: "Fechar" }).click();

  await page.getByRole("button", { name: "Sair" }).click();
  await expect(page).toHaveURL(/\/login$/);
  await login(page, "ASSINADO");
  await page.goto(`/app/contratos/${IDS.contract}`);
  await page.getByRole("button", { name: "Liberar contrato para Motor" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Liberar contrato para Motor" }).click();
  await expect(page.getByText(/Acao contratual registrada/)).toBeVisible();
  await expect(page.getByText(/Liberar para Motor nao cria Emprestimo/)).toBeVisible();
  await expect(page.getByRole("button", { name: /Criar Emprestimo|Pagamento|Parcela/i })).toHaveCount(0);
  await expect(page.getByRole("link", { name: /Motor|Pagamento|Parcela/i })).toHaveCount(0);
  await assertNoToken(page, context);
  const suffix = testInfo.project.name.startsWith("mobile") ? "contrato-flow-mobile" : "contrato-detail-desktop";
  await prepareEvidenceScreenshot(page);
  await page.screenshot({ animations: "disabled", caret: "initial", fullPage: false, path: resolve(`../docs/audits/evidence/frontend-mvp-imp-293-${suffix}.png`) });
});

test("RBAC leitura, empty, 404, 409 e 5xx permanecem seguros", async ({ page }) => {
  await login(page, "LEITURA");
  await page.goto("/app/contratos");
  await expect(page.getByText("Sem permissao para formalizar contrato.")).toBeVisible();
  await page.goto(`/app/contratos/${IDS.contract}`);
  await expect(page.getByText("Nenhuma acao contratual disponivel.")).toBeVisible();
  await page.getByRole("button", { name: "Sair" }).click();
  await expect(page).toHaveURL(/\/login$/);
  await login(page, "VAZIO");
  await page.goto("/app/contratos");
  await expect(page.getByText(/empty/)).toBeVisible();
  await page.getByRole("button", { name: "Sair" }).click();
  await expect(page).toHaveURL(/\/login$/);
  await login(page, "NAO-ENCONTRADO");
  await page.goto(`/app/contratos/${IDS.contract}`);
  await expect(page.getByRole("alert").filter({ hasText: "Contrato nao encontrado ou indisponivel." })).toBeVisible();
  await expect(page.getByText(/cross-carteira/)).toHaveCount(0);
  await page.getByRole("button", { name: "Sair" }).click();
  await expect(page).toHaveURL(/\/login$/);
  await login(page);
  await page.goto(`/app/contratos/${IDS.contract}`);
  await page.getByRole("button", { name: "Cancelar contrato" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Cancelar contrato" }).click();
  await expect(page.getByText(/Nao foi possivel concluir a operacao de Contratos\. Correlation ID:/)).toBeVisible();
  await page.getByRole("dialog").getByRole("button", { exact: true, name: "Fechar" }).click();
  await page.getByRole("button", { name: "Sair" }).click();
  await expect(page).toHaveURL(/\/login$/);
  await login(page, "ESTADOS");
  await page.goto("/app/contratos");
  await expect(page.getByText(/Correlation ID: corr-contratos-states-293/)).toBeVisible();
  await expect(page.getByText(/stack secreta/)).toHaveCount(0);
});
