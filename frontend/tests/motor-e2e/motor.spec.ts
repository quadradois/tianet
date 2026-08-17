import { resolve } from "node:path";

import { expect, test, type BrowserContext, type Page } from "@playwright/test";

const IDS = {
  contract: "00000000-0000-4000-8000-000000000030",
  loan: "00000000-0000-4000-8000-000000000040",
};

async function login(page: Page, institution = "ACME") {
  await page.goto("/login");
  await page.getByRole("textbox", { name: "Instituicao" }).fill(institution);
  await page.getByRole("textbox", { name: "E-mail" }).fill("operador@example.test");
  await page.getByLabel("Senha").fill("segredo-motor");
  await page.getByRole("button", { name: "Entrar" }).click();
  await expect(page).toHaveURL(/\/app(?:\?|$)/);
}

async function assertNoToken(page: Page, context: BrowserContext) {
  expect(await page.content()).not.toMatch(/access-(?:acme|leitura|nenhuma|estados)|refresh-/i);
  expect(await page.evaluate(() => ({ local: localStorage.length, session: sessionStorage.length }))).toEqual({ local: 0, session: 0 });
  expect((await context.cookies()).every((cookie) => cookie.httpOnly)).toBe(true);
}

async function prepareEvidenceScreenshot(page: Page) {
  await page.evaluate(() => {
    if (document.activeElement instanceof HTMLElement) document.activeElement.blur();
    const previous = document.querySelector("[data-evidence-stabilizer='motor']");
    previous?.remove();
    const style = document.createElement("style");
    style.dataset.evidenceStabilizer = "motor";
    style.textContent = "[aria-live='polite'] { visibility: hidden !important; }";
    document.head.appendChild(style);
    window.scrollTo(0, 0);
    // Congela o Correlation ID: e um UUID novo a cada requisicao. Mesmo dentro
    // da regiao escondida por `visibility: hidden` ele desestabiliza a captura,
    // porque a regiao continua ocupando layout e glifos diferentes quebram a
    // linha em pontos diferentes, deslocando tudo abaixo. A substituicao mantem
    // os mesmos 36 caracteres.
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

async function activateButton(page: Page, name: string) {
  const button = page.getByRole("button", { exact: true, name });
  await button.scrollIntoViewIfNeeded();
  await button.focus();
  await expect(button).toBeFocused();
  await page.keyboard.press("Enter");
}

test.beforeEach(async ({ page }) => {
  page.on("console", (message) => { if (message.type() === "error") throw new Error(`console error: ${message.text()}`); });
  page.on("pageerror", (error) => { throw error; });
});

test("lista Emprestimos e cria Emprestimo a partir de Contrato liberado sem Carteira do browser", async ({ page, context }, testInfo) => {
  const requests: string[] = [];
  page.on("request", (request) => requests.push(request.url()));
  await login(page);
  await page.goto(`/app/motor?contrato_id=${IDS.contract}&tenant_id=hostil&carteira_id=hostil`);
  await expect(page.getByRole("heading", { name: "Meus emprestimos" })).toBeVisible();
  await expect(page.getByRole("link", { exact: true, name: "Motor" })).toHaveAttribute("href", "/app/motor");
  await expect(page.getByLabel("Contrato liberado")).toHaveValue(IDS.contract);
  // A lista separa pelos estados que o backend devolveu e identifica o Devedor
  // pelo nome. O identificador do Emprestimo sai do corpo da tela.
  await expect(page.getByRole("heading", { name: /Em andamento \(1\)/ })).toBeVisible();
  await expect(page.getByRole("heading", { name: /Quitados \(1\)/ })).toBeVisible();
  await expect(page.getByRole("heading", { name: /Encerrados \(0\)/ })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Maria Souza" }).first()).toBeVisible();
  await expect(page.getByText(IDS.loan, { exact: true })).toHaveCount(0);
  await activateButton(page, "Criar Emprestimo");
  await expect(page.getByText(/Emprestimo criado pelo Motor/)).toBeVisible();
  await assertNoToken(page, context);
  expect(requests.every((url) => new URL(url).origin === "http://127.0.0.1:3106")).toBe(true);
  expect(requests.every((url) => !url.startsWith("http://127.0.0.1:3206"))).toBe(true);
  const suffix = testInfo.project.name.startsWith("mobile") ? "motor-list-mobile" : "motor-list-desktop";
  await prepareEvidenceScreenshot(page);
  await page.screenshot({ animations: "disabled", caret: "initial", fullPage: false, path: resolve(`../docs/audits/evidence/frontend-mvp-imp-294-${suffix}.png`) });
});

test("consulta detalhe, parcelas, saldo, memoria, pagamento e quitacao sem recalculo local", async ({ page, context }, testInfo) => {
  await login(page);
  await page.goto(`/app/motor/${IDS.loan}`);
  await expect(page.getByRole("heading", { name: new RegExp(`Emprestimo ${IDS.loan}`) })).toBeVisible();
  await expect(page.getByText("Saldo oficial")).toBeVisible();
  await expect(page.getByText("Memoria de calculo oficial")).toBeVisible();
  await expect(page.getByText("1010.00").first()).toBeVisible();
  await activateButton(page, "Gerar parcelas");
  await expect(page.getByText(/Plano de parcelas gerado pelo Motor/)).toBeVisible();
  await activateButton(page, "Registrar pagamento");
  await page.getByLabel("Valor recebido").fill("100.00");
  await activateButton(page, "Registrar pagamento");
  await expect(page.getByText(/Pagamento idempotente registrado pelo Motor/)).toBeVisible();
  await activateButton(page, "Executar quitacao");
  await expect(page.getByText(/Quitacao oficial executada pelo Motor/)).toBeVisible();
  await activateButton(page, "Registrar renegociacao");
  await expect(page.getByText(/Nao foi possivel concluir a operacao do Motor\. Correlation ID:/)).toBeVisible();
  await assertNoToken(page, context);
  const suffix = testInfo.project.name.startsWith("mobile") ? "pagamento-flow-mobile" : "emprestimo-detail-desktop";
  await prepareEvidenceScreenshot(page);
  await page.screenshot({ animations: "disabled", caret: "initial", fullPage: false, path: resolve(`../docs/audits/evidence/frontend-mvp-imp-294-${suffix}.png`) });
});

test("RBAC, empty, 404, 409, 5xx e estados permanecem seguros", async ({ page }) => {
  await login(page, "LEITURA");
  await page.goto("/app/motor");
  await expect(page.getByRole("button", { name: "Criar Emprestimo" })).toHaveCount(0);
  await page.goto(`/app/motor/${IDS.loan}`);
  await expect(page.getByText(/Registrar pagamento/)).toHaveCount(0);
  await page.getByRole("button", { name: "Sair" }).click();
  await expect(page).toHaveURL(/\/login$/);
  await login(page, "NENHUMA");
  await page.goto("/app/motor");
  await expect(page.getByText("denied", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Sair" }).click();
  await expect(page).toHaveURL(/\/login$/);
  await login(page, "VAZIO");
  await page.goto("/app/motor");
  // empty: cada grupo declara a propria ausencia.
  await expect(page.getByText(/Nenhum emprestimo em andamento/)).toBeVisible();
  await expect(page.getByText(/Nenhum emprestimo quitado ainda/)).toBeVisible();
  await expect(page.getByText(/Nenhum emprestimo encerrado/)).toBeVisible();
  await page.getByRole("button", { name: "Sair" }).click();
  await expect(page).toHaveURL(/\/login$/);
  await login(page, "NAO-ENCONTRADO");
  await page.goto(`/app/motor/${IDS.loan}`);
  await expect(page.getByRole("alert").filter({ hasText: "Emprestimo nao encontrado ou indisponivel." })).toBeVisible();
  await expect(page.getByText(/cross-carteira/)).toHaveCount(0);
  await page.getByRole("button", { name: "Sair" }).click();
  await expect(page).toHaveURL(/\/login$/);
  await login(page, "ESTADOS");
  await page.goto("/app/motor");
  await expect(page.getByText(/Correlation ID: corr-motor-states-294/)).toBeVisible();
  await expect(page.getByText(/stack secreta/)).toHaveCount(0);
});
