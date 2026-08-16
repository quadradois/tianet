import { resolve } from "node:path";

import { expect, test, type Page } from "@playwright/test";

const PROFILE_ID = "00000000-0000-4000-8000-000000000004";
const USER_ID = "00000000-0000-4000-8000-000000000005";

async function login(page: Page, institution = "ACME") {
  await page.context().clearCookies();
  await page.goto("/login", { waitUntil: "domcontentloaded" });
  await page.getByRole("textbox", { name: "Instituicao" }).fill(institution);
  await page.getByRole("textbox", { name: "E-mail" }).fill("operador@example.test");
  await page.getByLabel("Senha").fill("segredo-iam");
  await page.getByRole("button", { name: "Entrar" }).click();
  await expect(page).toHaveURL(/\/app(?:\?|$)/);
}

async function gotoIam(page: Page) {
  await page.goto(`/app/iam?perfil_id=${PROFILE_ID}&usuario_id=${USER_ID}`);
  await expect(page.getByRole("heading", { name: "Perfis, catalogo e atribuicoes" })).toBeVisible();
}

async function screenshotEvidence(page: Page, suffix: string) {
  await page.evaluate(() => {
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    const texts: Text[] = [];
    while (walker.nextNode()) texts.push(walker.currentNode as Text);
    for (const text of texts) text.data = text.data.replace(/Correlation ID: [A-Za-z0-9._:-]+/g, "Correlation ID: corr-evidence-299");
  });
  await page.screenshot({
    animations: "disabled",
    caret: "initial",
    fullPage: false,
    path: resolve(`../docs/audits/evidence/frontend-mvp-imp-299-${suffix}.png`),
  });
}

async function submitByName(page: Page, name: string) {
  const button = page.getByRole("button", { name });
  await button.scrollIntoViewIfNeeded();
  await button.click({ force: true });
}

test("renderiza IAM permitido e captura desktop/mobile", async ({ page }, testInfo) => {
  const backendHits: string[] = [];
  page.on("request", (request) => {
    if (request.url().includes("127.0.0.1:3211/iam") && !request.url().includes("/iam/contexto-atual")) backendHits.push(request.url());
  });
  await login(page);
  await gotoIam(page);
  await expect(page.getByText("Administrador IAM").first()).toBeVisible();
  await expect(page.getByRole("region", { name: "Perfis IAM com overflow" })).toBeVisible();
  await expect(page.getByRole("region", { name: "Catalogo de Permissoes com overflow" })).toBeVisible();
  expect(backendHits).toEqual([]);
  await screenshotEvidence(page, testInfo.project.name.includes("mobile") ? "iam-mobile" : "iam-desktop");
});

test("executa comandos IAM sem expor token nem listar Usuarios", async ({ page }) => {
  await login(page);
  await gotoIam(page);
  await page.locator('input[name="nome"]').first().fill("Auditor");
  await submitByName(page, "Criar Perfil");
  await expect(page.getByText(/Perfil criado/)).toBeVisible();
  await page.locator("#iam-rename-id").fill(PROFILE_ID);
  await page.locator("#iam-rename-nome").fill("Auditor Senior");
  await submitByName(page, "Renomear Perfil");
  await expect(page.getByText(/Perfil renomeado/)).toBeVisible();
  await page.locator("#iam-inactivate-id").fill(PROFILE_ID);
  await submitByName(page, "Inativar Perfil");
  await expect(page.getByText(/Perfil inativado/)).toBeVisible();
  await page.locator("#iam-add-perfil").fill(PROFILE_ID);
  await page.locator("#iam-add-codigo").fill("perfil.ler");
  await submitByName(page, "Associar permissao");
  await expect(page.getByText(/Permissao associada/)).toBeVisible();
  await page.locator("#iam-remove-perfil").fill(PROFILE_ID);
  await page.locator("#iam-remove-codigo").fill("perfil.ler");
  await submitByName(page, "Remover permissao");
  await expect(page.getByText(/Permissao removida/)).toBeVisible();
  await page.locator("#iam-assign-user").fill(USER_ID);
  await page.locator("#iam-assign-perfil").fill(PROFILE_ID);
  await submitByName(page, "Atribuir Perfil ao Usuario");
  await expect(page.getByText(/Perfil atribuido/)).toBeVisible();
  await page.locator("#iam-remove-user").fill(USER_ID);
  await submitByName(page, "Remover Perfil do Usuario");
  await expect(page.getByText(/Perfil removido do Usuario/)).toBeVisible();
  await expect(page.getByText(/access-|refresh-|Bearer/)).toHaveCount(0);
  await expect(page.getByText(/credencial/i)).toHaveCount(0);
});

test("observa denied, empty, 404, 409, 422 e 5xx seguros", async ({ page }, testInfo) => {
  await login(page, "nenhuma");
  await gotoIam(page);
  await expect(page.getByText(/Sem permissao/).first()).toBeVisible();
  await login(page, "vazio");
  await gotoIam(page);
  await expect(page.getByText(/empty:/)).toBeVisible();
  await login(page, "nao-encontrado");
  await gotoIam(page);
  await expect(page.getByRole("alert").first()).toContainText("IAM nao encontrado ou indisponivel");
  await expect(page.getByText("usuario interno")).toHaveCount(0);
  await login(page, "conflito");
  await gotoIam(page);
  await page.locator('input[name="nome"]').first().fill("Auditor");
  await submitByName(page, "Criar Perfil");
  await expect(page.getByText(/Conflito de IAM/)).toBeVisible();
  await login(page, "regra");
  await gotoIam(page);
  await page.locator('input[name="nome"]').first().fill("Auditor");
  await submitByName(page, "Criar Perfil");
  await expect(page.getByText(/Regra IAM rejeitou/)).toBeVisible();
  await login(page, "estados");
  await gotoIam(page);
  const alert = page.getByRole("alert").first();
  await expect(alert).toContainText("Servico IAM temporariamente indisponivel.");
  await expect(page.getByText("stack segredo iam")).toHaveCount(0);
  await alert.scrollIntoViewIfNeeded();
  if (testInfo.project.name.includes("desktop")) await screenshotEvidence(page, "iam-states-desktop");
  if (testInfo.project.name.includes("mobile")) await screenshotEvidence(page, "iam-states-mobile");
});
