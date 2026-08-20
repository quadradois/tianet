import { resolve } from "node:path";

import { expect, test, type Page } from "@playwright/test";

const periodQuery = "data_referencia=2026-08-14&inicio=2026-08-01&fim=2026-08-31";

async function login(page: Page, institution = "ACME") {
  await page.context().clearCookies();
  await page.goto("/login", { waitUntil: "domcontentloaded" });
  await page.getByRole("textbox", { name: "Instituicao" }).fill(institution);
  await page.getByRole("textbox", { name: "E-mail" }).fill("operador@example.test");
  await page.getByLabel("Senha").fill("segredo-relatorios");
  await page.getByRole("button", { name: "Entrar" }).click();
  await expect(page).toHaveURL(/\/app(?:\?|$)/);
}

async function gotoRelatorios(page: Page) {
  await page.goto(`/app/relatorios?${periodQuery}`);
  await expect(page.getByRole("heading", { exact: true, name: "Relatorios" })).toBeVisible();
}

async function screenshotEvidence(page: Page, suffix: string) {
  await page.evaluate(() => {
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    const texts: Text[] = [];
    while (walker.nextNode()) texts.push(walker.currentNode as Text);
    for (const text of texts) text.data = text.data.replace(/Correlation ID: [A-Za-z0-9._:-]+/g, "Correlation ID: corr-evidence-297");
  });
  await page.screenshot({
    animations: "disabled",
    caret: "initial",
    fullPage: false,
    path: resolve(`../docs/audits/evidence/frontend-mvp-imp-297-${suffix}.png`),
  });
}

test("renderiza Relatorios oficiais e captura desktop/mobile", async ({ page }, testInfo) => {
  const backendHits: string[] = [];
  page.on("request", (request) => {
    if (request.url().includes("127.0.0.1:3209/credit")) backendHits.push(request.url());
  });
  await login(page, "ACME");
  await gotoRelatorios(page);
  await expect(page.getByText("R$ 98.765,43")).toBeVisible();
  await expect(page.getByRole("region", { name: "Acertos oficiais" })).toBeVisible();
  await expect(page.getByRole("region", { name: "Pagamentos oficiais" })).toBeVisible();
  expect(backendHits).toEqual([]);
  await page.getByText("R$ 98.765,43").scrollIntoViewIfNeeded();
  const suffix = testInfo.project.name.includes("mobile") ? "relatorios-list-mobile" : "relatorios-list-desktop";
  await screenshotEvidence(page, suffix);
});

test("observa fluxo oficial, overflow e captura desktop", async ({ page }, testInfo) => {
  await login(page, "ACME");
  await gotoRelatorios(page);
  await page.getByRole("region", { name: "Acertos e recebimentos por dia" }).focus();
  await expect(page.getByRole("region", { name: "Acertos e recebimentos por dia" })).toBeFocused();
  expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(0);
  await page.getByRole("region", { name: "Acertos e recebimentos por dia" }).scrollIntoViewIfNeeded();
  if (testInfo.project.name.includes("desktop")) await screenshotEvidence(page, "fluxo-desktop");
});

test("observa missing, denied, empty, 404 e 5xx sem vazar detalhe backend", async ({ page }, testInfo) => {
  await login(page, "ACME");
  await page.goto("/app/relatorios");
  await expect(page.getByText(/Defina periodo/)).toBeVisible();
  await login(page, "nenhuma");
  await gotoRelatorios(page);
  await expect(page.getByText("Sem permissao").first()).toBeVisible();
  await login(page, "vazio");
  await gotoRelatorios(page);
  await expect(page.getByText(/empty:/).first()).toBeVisible();
  await login(page, "nao-encontrado");
  await gotoRelatorios(page);
  await expect(page.getByRole("alert").first()).toContainText("Dados de relatorio nao encontrados ou indisponiveis.");
  await expect(page.getByText("detalhe cross tenant")).toHaveCount(0);
  await login(page, "estados");
  await gotoRelatorios(page);
  await expect(page.getByRole("alert").first()).toContainText("Servico temporariamente indisponivel.");
  await expect(page.getByText("stack secreta")).toHaveCount(0);
  await page.getByRole("alert").first().scrollIntoViewIfNeeded();
  if (testInfo.project.name.includes("mobile")) await screenshotEvidence(page, "relatorios-states-mobile");
});
