import { resolve } from "node:path";

import { expect, test, type BrowserContext, type Page } from "@playwright/test";

async function login(page: Page, institution = "ACME") {
  await page.goto("/login");
  await page.getByRole("textbox", { name: "Instituicao" }).fill(institution);
  await page.getByRole("textbox", { name: "E-mail" }).fill("operador@example.test");
  await page.getByLabel("Senha").fill("segredo-dashboard");
  await page.getByRole("button", { name: "Entrar" }).click();
}

async function assertNoToken(page: Page, context: BrowserContext) {
  expect(await page.content()).not.toMatch(/access-(?:acme|old|partial|empty|states)|refresh-/i);
  expect(await page.evaluate(() => ({ local: localStorage.length, session: sessionStorage.length }))).toEqual({ local: 0, session: 0 });
  expect((await context.cookies()).every((cookie) => cookie.httpOnly)).toBe(true);
}

test.beforeEach(async ({ page }) => {
  page.on("console", (message) => { if (message.type() === "error") throw new Error(`console error: ${message.text()}`); });
  page.on("pageerror", (error) => { throw error; });
});

test("login compoe o Dashboard completo sem expor token ou backend ao browser", async ({ page, context }, testInfo) => {
  const requests: string[] = [];
  page.on("request", (request) => requests.push(request.url()));
  await login(page);
  await expect(page).toHaveURL(/\/app\?data_referencia=\d{4}-\d{2}-\d{2}$/);
  await expect(page.getByRole("heading", { name: "Inicio" })).toBeVisible();
  await expect(page.getByText("12345.67")).toBeVisible();
  await expect(page.locator("dd:visible, td:visible").filter({ hasText: /^pendente$/ }).first()).toBeVisible();
  await expect(page.getByText("Contato operacional com o cliente")).toBeVisible();
  await expect(page.getByText("Caso operacional 1 com descricao extensa para validar overflow contido")).toBeVisible();
  await assertNoToken(page, context);
  expect(requests.every((url) => new URL(url).origin === "http://127.0.0.1:3102")).toBe(true);
  expect(await page.getByRole("link").evaluateAll((links) => links.map((link) => link.getAttribute("href")))).not.toEqual(expect.arrayContaining(["/devedores", "/comercial", "/contratos"]));
  expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(0);
  const suffix = testInfo.project.name.startsWith("mobile") ? "mobile" : "desktop";
  await page.screenshot({ animations: "disabled", caret: "initial", fullPage: false, path: resolve(`../docs/audits/evidence/frontend-mvp-imp-290-dashboard-${suffix}.png`) });
});

test("RBAC parcial e perfil nulo nao disparam navegacao ou dados indevidos", async ({ page }) => {
  await login(page, "PARCIAL");
  await expect(page.getByText("12345.67")).toBeVisible();
  await expect(page.getByText("Sem permissao")).toHaveCount(2);
  await page.getByRole("button", { name: "Sair" }).click();
  await login(page, "NENHUMA");
  await expect(page.getByText("Sem permissao")).toHaveCount(4);
  await expect(page.getByRole("navigation", { name: "Navegacao principal" }).getByRole("link")).toHaveCount(0);
});

test("distingue loading, empty e periodo invalido antes de consultar dados", async ({ page }) => {
  await login(page, "LENTO");
  await expect(page.getByRole("status", { name: /Carregando/ }).first()).toBeVisible();
  await expect(page.getByText("12345.67")).toBeVisible();
  await page.getByRole("button", { name: "Sair" }).click();
  await login(page, "VAZIO");
  await expect(page.getByText(/Nenhum acerto/)).toBeVisible();
  await expect(page.getByText(/Nenhum compromisso/)).toBeVisible();
  await expect(page.getByText(/Nenhum caso ativo/)).toBeVisible();
  await page.goto("/app?data_referencia=2026-02-30");
  await expect(page.getByText("Periodo invalido (400)", { exact: true })).toBeVisible();
});

test("isola falhas por secao, preserva 404 neutro e captura estados dark", async ({ page }, testInfo) => {
  await login(page, "ESTADOS");
  await expect(page.getByText("Nao foi possivel carregar")).toHaveCount(2);
  await expect(page.getByText(/Correlation ID:/)).toHaveCount(2);
  await expect(page.getByText(/Nenhum acerto/)).toBeVisible();
  await expect(page.getByText("Sem permissao")).toHaveCount(0);
  await expect(page.getByText(/stack secreta|regra interna/)).toHaveCount(0);
  await page.evaluate(() => document.documentElement.classList.add("dark"));
  const collection = page.getByRole("region", { name: "Fila de cobranca" });
  if (await collection.count()) await expect(collection).toBeVisible();
  const suffix = testInfo.project.name.startsWith("mobile") ? "mobile" : "desktop";
  await page.screenshot({ animations: "disabled", caret: "initial", fullPage: false, path: resolve(`../docs/audits/evidence/frontend-mvp-imp-290-dashboard-states-${suffix}.png`) });
  await page.getByRole("button", { name: "Sair" }).click();
  await login(page, "NAO-ENCONTRADO");
  await expect(page.getByText("Dados nao encontrados ou indisponiveis.")).toBeVisible();
  await expect(page.getByText(/cross tenant/)).toHaveCount(0);
});

test("401 isolado em uma secao tenta um bootstrap e falha fechado sem loop", async ({ page }) => {
  const bootstraps: string[] = [];
  page.on("request", (request) => { if (new URL(request.url()).pathname === "/api/auth/bootstrap") bootstraps.push(request.url()); });
  await login(page, "SECAO-EXPIRADA");
  await expect.poll(() => bootstraps.length, { timeout: 15_000 }).toBe(1);
  await expect(page).toHaveURL(/\/login$/, { timeout: 15_000 });
  expect(bootstraps).toHaveLength(1);
});
