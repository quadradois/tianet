import { resolve } from "node:path";

import { expect, test, type Page } from "@playwright/test";

const JOB_ID = "00000000-0000-4000-8000-000000000081";
const NOTIFICATION_ID = "00000000-0000-4000-8000-000000000082";
const TEMPLATE_ID = "00000000-0000-4000-8000-000000000083";

function emailForInstitution(institution: string): string {
  const mode = institution.toLowerCase();
  return mode === "acme" ? "operador@example.test" : `operador+${mode}@example.test`;
}
async function login(page: Page, institution = "ACME") {
  await page.context().clearCookies();
  await page.goto("/login", { waitUntil: "domcontentloaded" });
  await page.getByRole("textbox", { name: "E-mail" }).fill(emailForInstitution(institution));
  await page.getByLabel("Senha").fill("segredo-automacao");
  await page.getByRole("button", { name: "Entrar" }).click();
  await expect(page).toHaveURL(/\/app(?:\?|$)/);
}

async function gotoAutomacao(page: Page) {
  await page.goto(`/app/automacao?job_id=${JOB_ID}&notification_id=${NOTIFICATION_ID}`);
  await expect(page.getByRole("heading", { name: "Jobs, Templates e Notificacoes" })).toBeVisible();
}

async function screenshotEvidence(page: Page, suffix: string) {
  await page.evaluate(() => {
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    const texts: Text[] = [];
    while (walker.nextNode()) texts.push(walker.currentNode as Text);
    for (const text of texts) text.data = text.data.replace(/Correlation ID: [A-Za-z0-9._:-]+/g, "Correlation ID: corr-evidence-300");
  });
  await page.screenshot({
    animations: "disabled",
    caret: "initial",
    fullPage: false,
    path: resolve(`../docs/audits/evidence/frontend-mvp-imp-300-${suffix}.png`),
  });
}

async function submitByName(page: Page, name: string) {
  const button = page.getByRole("button", { name });
  await button.scrollIntoViewIfNeeded();
  await button.click({ force: true });
}

test("renderiza Automacao operacional e captura desktop/mobile", async ({ page }, testInfo) => {
  const backendHits: string[] = [];
  page.on("request", (request) => {
    if (request.url().includes("127.0.0.1:3212/credit/automacao") || request.url().includes("127.0.0.1:3212/credit/notificacoes")) backendHits.push(request.url());
  });
  await login(page);
  await gotoAutomacao(page);
  await expect(page.getByText("corr-job-official")).toBeVisible();
  await expect(page.getByRole("region", { name: "Jobs de Automacao com overflow" })).toBeVisible();
  expect(backendHits).toEqual([]);
  await screenshotEvidence(page, testInfo.project.name.includes("mobile") ? "automacao-mobile" : "automacao-desktop");
});

test("executa comandos Automacao sem expor token", async ({ page }) => {
  await login(page);
  await gotoAutomacao(page);
  await page.locator("#automacao-cancel-job").fill(JOB_ID);
  await submitByName(page, "Cancelar job");
  await expect(page.getByText(/Job recebeu pedido/)).toBeVisible();
  await page.locator("#automacao-retry-job").fill(JOB_ID);
  await submitByName(page, "Retry job");
  await expect(page.getByText(/Retry tecnico solicitado/)).toBeVisible();
  await page.locator("#automacao-template-codigo").fill("cobranca-lembrete");
  await page.locator("#automacao-template-versao").fill("1");
  await page.locator("#automacao-template-assunto").fill("Aviso");
  await page.locator("#automacao-template-corpo").fill("Mensagem governada");
  await submitByName(page, "Criar template");
  await expect(page.getByText(/Template criado/)).toBeVisible();
  await page.locator("#automacao-approve-template").fill(TEMPLATE_ID);
  await submitByName(page, "Aprovar template");
  await expect(page.getByText(/Template aprovado/)).toBeVisible();
  await page.locator("#automacao-activate-template").fill(TEMPLATE_ID);
  await submitByName(page, "Ativar template");
  await expect(page.getByText(/Template ativado/)).toBeVisible();
  await page.locator("#automacao-reconcile-notification").fill(NOTIFICATION_ID);
  await page.locator("#automacao-reconcile-provider").fill("provider-ok");
  await page.locator("#automacao-reconcile-motivo").fill("Conferencia manual");
  await submitByName(page, "Conciliar notificacao");
  await expect(page.getByText(/Notificacao conciliada/)).toBeVisible();
  await expect(page.getByText(/access-|refresh-|Bearer/)).toHaveCount(0);
});

test("observa denied, empty, 404, 409, 422 e 500 seguros", async ({ page }, testInfo) => {
  await login(page, "nenhuma");
  await gotoAutomacao(page);
  await expect(page.getByText(/Sem permissao/).first()).toBeVisible();
  await login(page, "vazio");
  await gotoAutomacao(page);
  await expect(page.getByText(/empty:/).first()).toBeVisible();
  await login(page, "nao-encontrado");
  await gotoAutomacao(page);
  await expect(page.getByRole("alert").first()).toContainText("Automacao nao encontrada ou indisponivel");
  await expect(page.getByText("detalhe interno")).toHaveCount(0);
  await login(page, "conflito");
  await gotoAutomacao(page);
  await page.locator("#automacao-cancel-job").fill(JOB_ID);
  await submitByName(page, "Cancelar job");
  await expect(page.getByText(/Transicao indisponivel/)).toBeVisible();
  await login(page, "regra");
  await gotoAutomacao(page);
  await page.locator("#automacao-reconcile-notification").fill(NOTIFICATION_ID);
  await page.locator("#automacao-reconcile-provider").fill("provider-ok");
  await page.locator("#automacao-reconcile-motivo").fill("Conferencia manual");
  await submitByName(page, "Conciliar notificacao");
  await expect(page.getByText(/Regra de Automacao rejeitou/)).toBeVisible();
  await login(page, "estados");
  await gotoAutomacao(page);
  await expect(page.getByRole("alert").first()).toContainText("Servico de Automacao temporariamente indisponivel.");
  await expect(page.getByText("stack segredo automacao")).toHaveCount(0);
  if (testInfo.project.name.includes("desktop")) await screenshotEvidence(page, "automacao-states-desktop");
  if (testInfo.project.name.includes("mobile")) await screenshotEvidence(page, "automacao-states-mobile");
});
