import { resolve } from "node:path";

import { expect, test, type BrowserContext, type Page } from "@playwright/test";

const IDS = {
  contract: "00000000-0000-4000-8000-000000000030",
  loan: "00000000-0000-4000-8000-000000000040",
};

function emailForInstitution(institution: string): string {
  const mode = institution.toLowerCase();
  return mode === "acme" ? "operador@example.test" : `operador+${mode}@example.test`;
}
async function login(page: Page, institution = "ACME") {
  await page.goto("/login");
  await page.getByRole("textbox", { name: "E-mail" }).fill(emailForInstitution(institution));
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
  await expect(page.locator(`[role="status"][aria-label^="loading"], [role="status"][aria-label^="Carregando"]`)).toHaveCount(0);
  await page.evaluate(async () => {
    if (document.activeElement instanceof HTMLElement) document.activeElement.blur();
    const previous = document.querySelector("[data-evidence-stabilizer='motor']");
    previous?.remove();
    const style = document.createElement("style");
    style.dataset.evidenceStabilizer = "motor";
    style.textContent = "html, body, * { scroll-behavior: auto !important; } [aria-live='polite'] { visibility: hidden !important; } input[data-evidence-uuid='true'] { font-family: ui-monospace, SFMono-Regular, Menlo, monospace !important; font-size: 10px !important; font-style: normal !important; font-weight: 400 !important; letter-spacing: 0px !important; line-height: 1.4 !important; box-sizing: border-box !important; width: 100% !important; max-width: 100% !important; overflow: visible !important; text-overflow: clip !important; }";
    document.head.appendChild(style);
    const zeroScroll = () => {
      window.scrollTo(0, 0);
      document.documentElement.scrollLeft = 0;
      document.documentElement.scrollTop = 0;
      if (document.body) {
        document.body.scrollLeft = 0;
        document.body.scrollTop = 0;
      }
      for (const el of Array.from(document.querySelectorAll("main, div, section, article, aside, input, textarea, select, [role='region'], [role='dialog']"))) {
        const element = el as HTMLElement;
        if (element.scrollLeft !== 0) element.scrollLeft = 0;
        if (element.scrollTop !== 0) element.scrollTop = 0;
        if (element instanceof HTMLInputElement || element instanceof HTMLTextAreaElement) {
          try {
            if (element.selectionStart !== null && element.selectionEnd !== null) {
              if (element.selectionStart !== 0 || element.selectionEnd !== 0) element.setSelectionRange(0, 0);
            }
          } catch {
            // Tipos de input sem suporte a selecao (number, checkbox, etc.): ignora.
          }
        }
      }
    };
    zeroScroll();
    // Congela o Correlation ID: e um UUID novo a cada requisicao. Mesmo dentro
    // da regiao escondida por `visibility: hidden` ele desestabiliza a captura,
    // porque a regiao continua ocupando layout e glifos diferentes quebram a
    // linha em pontos diferentes, deslocando tudo abaixo. A substituicao mantem
    // os mesmos 36 caracteres.
    // Substitui o UUID **dentro** do texto, e nao apenas o no que seja so o
    // UUID: neste modulo o identificador vem concatenado na mesma string da
    // mensagem, e a versao anterior desta regra nao o alcancava.
    const FIXED_UUID = "00000000-0000-4000-8000-00000000evid";
    const uuidRegex = new RegExp("[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", "gi");
    const corrRegex = /Correlation ID:\s*corr-[A-Za-z0-9._:-]+/g;
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    const nodes: Text[] = [];
    let current = walker.nextNode();
    while (current) {
      nodes.push(current as Text);
      current = walker.nextNode();
    }
    for (const textNode of nodes) {
      const original = textNode.data;
      const normalized = original.replace(uuidRegex, FIXED_UUID).replace(corrRegex, "Correlation ID: corr-evidence-294");
      if (normalized !== original) textNode.data = normalized;
    }
    for (const input of Array.from(document.querySelectorAll("input"))) {
      const element = input as HTMLInputElement;
      if (/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(element.value)) {
        element.dataset.evidenceUuid = "true";
      }
    }
    await document.fonts.ready;
    await new Promise<void>((resolve) => requestAnimationFrame(() => requestAnimationFrame(() => resolve())));
    zeroScroll();
    if (window.scrollX !== 0 || window.scrollY !== 0) throw new Error(`evidence scroll not zeroed: ${window.scrollX},${window.scrollY}`);
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
  await expect(page.getByRole("link", { exact: true, name: "Emprestimos" })).toHaveAttribute("href", "/app/motor");
  // O caminho principal de lancar e o wizard. A criacao por Contrato continua
  // possivel, mas recolhida: precisa ser aberta de proposito.
  await expect(page.getByLabel("Contrato liberado")).toBeHidden();
  await page.getByText("Criar a partir de um contrato ja existente").click();
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
  await page.screenshot({ animations: "disabled", caret: "hide", fullPage: false, path: resolve(`../docs/audits/evidence/frontend-mvp-imp-294-${suffix}.png`) });
});

test("consulta detalhe, parcelas, saldo, memoria, pagamento e quitacao sem recalculo local", async ({ page, context }, testInfo) => {
  await login(page);
  await page.goto(`/app/motor/${IDS.loan}`);
  // O painel abre dizendo de quem e o emprestimo, e nao qual e o identificador.
  await expect(page.getByRole("heading", { name: "Maria Souza" })).toBeVisible();
  await expect(page.getByText("Deve hoje")).toBeVisible();
  await expect(page.getByText("Proximo acerto")).toBeVisible();
  // O extrato substitui a tabela de parcelas (DR-004).
  await expect(page.getByText("Como esta a divida hoje")).toBeVisible();
  await expect(page.getByText(IDS.loan, { exact: true })).toHaveCount(0);
  // O cartao antigo saiu: repetia o extrato.
  await expect(page.getByText("Quanto ainda falta")).toHaveCount(0);
  await expect(page.getByText("Como a conta foi feita")).toBeVisible();
  await expect(page.getByText("R$ 1.010,00").first()).toBeVisible();
  // As operacoes ficam em um drawer: primeiro entender, depois agir.
  await expect(page.getByRole("button", { name: "Registrar pagamento", exact: true })).toBeHidden();
  await page.getByRole("button", { name: "Operar emprestimo" }).click();
  await expect(page.getByRole("dialog", { name: "Operacoes deste emprestimo" })).toBeVisible();
  // Nao ha plano a gerar no emprestimo livre (DR-004).
  await expect(page.getByRole("button", { name: "Gerar parcelas", exact: true })).toHaveCount(0);
  await page.getByLabel("Quanto o devedor pagou").fill("100,00");
  await activateButton(page, "Registrar pagamento");
  await expect(page.getByText(/Pagamento idempotente registrado pelo Motor/)).toBeVisible();
  await activateButton(page, "Quitar emprestimo");
  await expect(page.getByText(/Quitacao oficial executada pelo Motor/)).toBeVisible();
  await activateButton(page, "Renegociar condicoes");
  await expect(page.getByText(/Nao foi possivel concluir a operacao do Motor\. Correlation ID:/)).toBeVisible();
  await assertNoToken(page, context);
  const suffix = testInfo.project.name.startsWith("mobile") ? "pagamento-flow-mobile" : "emprestimo-detail-desktop";
  await prepareEvidenceScreenshot(page);
  await page.screenshot({ animations: "disabled", caret: "hide", fullPage: false, path: resolve(`../docs/audits/evidence/frontend-mvp-imp-294-${suffix}.png`) });
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
  await expect(page.getByText("Sem permissao", { exact: true }).first()).toBeVisible();
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
