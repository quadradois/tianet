import { resolve } from "node:path";

import { expect, test, type BrowserContext, type Page } from "@playwright/test";

async function login(page: Page, institution = "ACME") {
  await page.goto("/login");
  await page.getByRole("textbox", { name: "Instituicao" }).fill(institution);
  await page.getByRole("textbox", { name: "E-mail" }).fill("operador@example.test");
  await page.getByLabel("Senha").fill("segredo-devedores");
  await page.getByRole("button", { name: "Entrar" }).click();
  await expect(page).toHaveURL(/\/app(?:\?|$)/);
}

async function assertNoToken(page: Page, context: BrowserContext) {
  expect(await page.content()).not.toMatch(/access-(?:acme|leitura|nenhuma|estados)|refresh-/i);
  expect(await page.evaluate(() => ({ local: localStorage.length, session: sessionStorage.length }))).toEqual({ local: 0, session: 0 });
  expect((await context.cookies()).every((cookie) => cookie.httpOnly)).toBe(true);
}

/**
 * Congela o Correlation ID antes da captura de evidencia.
 *
 * O identificador e um UUID novo a cada requisicao e aparece impresso na tela
 * apos Inativar/Reativar. Sem isto a evidencia visual nunca se repete: duas
 * execucoes identicas produzem PNGs diferentes, e o pino de SHA no relatorio
 * vira ruido em vez de prova. A substituicao mantem os mesmos 36 caracteres,
 * para nao deslocar o layout.
 */
async function freezeCorrelationIds(page: Page) {
  await page.evaluate(() => {
    const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    for (let node = walker.nextNode(); node; node = walker.nextNode()) {
      const value = node.nodeValue?.trim() ?? "";
      if (UUID.test(value) && (node.parentElement?.textContent ?? "").includes("Correlation ID")) {
        node.nodeValue = "00000000-0000-4000-8000-00000000evid";
      }
    }
  });
}

test.beforeEach(async ({ page }) => {
  page.on("console", (message) => { if (message.type() === "error") throw new Error(`console error: ${message.text()}`); });
  page.on("pageerror", (error) => { throw error; });
});

test("lista e consulta Devedores usando somente BFF same-origin", async ({ page, context }, testInfo) => {
  const requests: string[] = [];
  page.on("request", (request) => requests.push(request.url()));
  await login(page);
  await page.getByRole("link", { name: "Devedores" }).click();
  await expect(page).toHaveURL(/\/app\/devedores$/);
  await expect(page.getByRole("heading", { name: "Devedores" })).toBeVisible();
  await expect(page.getByText("Cliente Devedor 1 com nome extenso para overflow")).toBeVisible();
  await assertNoToken(page, context);
  expect(requests.every((url) => new URL(url).origin === "http://127.0.0.1:3103")).toBe(true);
  expect(requests.some((url) => url.includes("carteira_id=") || url.includes("tenant_id="))).toBe(false);
  const suffix = testInfo.project.name.startsWith("mobile") ? "mobile" : "desktop";
  await page.screenshot({ animations: "disabled", caret: "initial", fullPage: false, path: resolve(`../docs/audits/evidence/frontend-mvp-imp-291-devedores-list-${suffix}.png`) });
});

test("detalhe, historico e comandos idempotentes respeitam RBAC exato", async ({ page }, testInfo) => {
  await login(page);
  await page.goto("/app/devedores");
  await page.getByRole("link", { name: "Consultar" }).first().click();
  await expect(page.getByRole("heading", { name: "Cliente Devedor" })).toBeVisible();
  await expect(page.getByText("criar.sucesso")).toBeVisible();
  // Abrir o Devedor ja mostra a situacao dos emprestimos dele, agrupada pelo
  // estado que o backend devolveu. Grupo sem nada nao aparece.
  await expect(page.getByRole("heading", { name: "Emprestimos deste devedor" })).toBeVisible();
  await expect(page.getByRole("heading", { name: /Em andamento \(1\)/ })).toBeVisible();
  await expect(page.getByRole("heading", { name: /Quitados \(1\)/ })).toBeVisible();
  await expect(page.getByRole("heading", { name: /Encerrados/ })).toHaveCount(0);
  await page.getByRole("button", { name: "Inativar" }).click();
  await expect(page.getByText(/Devedor inativado com sucesso/)).toBeVisible();
  await page.getByRole("button", { name: "Reativar" }).click();
  await expect(page.getByText(/Devedor reativado com sucesso/)).toBeVisible();
  const suffix = testInfo.project.name.startsWith("mobile") ? "devedor-form-mobile" : "devedor-detail-desktop";
  await freezeCorrelationIds(page);
  await page.screenshot({ animations: "disabled", caret: "initial", fullPage: false, path: resolve(`../docs/audits/evidence/frontend-mvp-imp-291-${suffix}.png`) });
  await page.getByRole("button", { name: "Sair" }).click();
  await expect(page).toHaveURL(/\/login$/);
  await login(page, "LEITURA");
  await page.goto("/app/devedores/00000000-0000-4000-8000-000000000010");
  await expect(page.getByText("Sem permissao de atualizar Devedor.")).toBeVisible();
  await expect(page.getByText("Sem permissao de inativar Devedor.")).toBeVisible();
  // Sem motor.emprestimo.ler o bloco nega, e o detalhe do Devedor continua util.
  await expect(page.getByText("Modulo Motor indisponivel para as permissoes efetivas atuais.")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Cliente Devedor" })).toBeVisible();
});

test("busca por documento, estados vazios e erros 404/409/422 sao seguros", async ({ page }) => {
  await login(page);
  await page.goto("/app/devedores?documento=12345678909&carteira_id=hostil&tenant_id=hostil");
  await expect(page.getByText("Resultado por documento")).toBeVisible();
  await expect(page.getByText("Cliente Devedor")).toBeVisible();
  await page.getByRole("button", { name: "Sair" }).click();
  await expect(page).toHaveURL(/\/login$/);
  await login(page, "VAZIO");
  await page.goto("/app/devedores");
  await expect(page.getByText(/empty/)).toBeVisible();
  await page.getByRole("button", { name: "Sair" }).click();
  await expect(page).toHaveURL(/\/login$/);
  await login(page, "NAO-ENCONTRADO");
  await page.goto("/app/devedores/00000000-0000-4000-8000-000000000010");
  await expect(page.getByRole("alert").filter({ hasText: "Devedor nao encontrado ou indisponivel." }).first()).toBeVisible();
  await expect(page.getByText(/cross-carteira/)).toHaveCount(0);
});

test("falhas parciais mostram correlation sem detalhe interno", async ({ page }) => {
  await login(page, "ESTADOS");
  await page.goto("/app/devedores");
  await expect(page.getByText(/Correlation ID: corr-devedores-states-291/)).toBeVisible();
  await expect(page.getByText(/stack secreta/)).toHaveCount(0);
});
