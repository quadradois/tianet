import { resolve } from "node:path";

import { expect, test, type Page } from "@playwright/test";

function emailForInstitution(institution: string): string {
  const mode = institution.toLowerCase();
  return mode === "acme" ? "operador@example.test" : `operador+${mode}@example.test`;
}
async function login(page: Page, institution = "ACME") {
  await page.goto("/login");
  await page.getByRole("textbox", { name: "E-mail" }).fill(emailForInstitution(institution));
  await page.getByLabel("Senha").fill("segredo-agenda");
  await page.getByRole("button", { name: "Entrar" }).click();
  await expect(page).toHaveURL(/\/app(?:\?|$)/);
}

async function gotoAgenda(page: Page) {
  await page.goto("/app/agenda");
  await expect(page.getByRole("heading", { name: "Agenda e Comunicacao" })).toBeVisible();
}

async function screenshotEvidence(page: Page, suffix: string) {
  await page.evaluate(() => {
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    const texts: Text[] = [];
    while (walker.nextNode()) texts.push(walker.currentNode as Text);
    for (const text of texts) {
      text.data = text.data.replace(/Correlation ID: [A-Za-z0-9._:-]+/g, "Correlation ID: corr-evidence-296");
    }
  });
  await page.screenshot({
    animations: "disabled",
    caret: "initial",
    fullPage: false,
    path: resolve(`../docs/audits/evidence/frontend-mvp-imp-296-${suffix}.png`),
  });
}

test("renderiza Agenda e Comunicacao e captura desktop/mobile", async ({ page }, testInfo) => {
  await login(page, "ACME");
  await gotoAgenda(page);
  await expect(page.getByRole("cell", { name: "Retorno operacional" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Historico de comunicacao" })).toBeVisible();
  await expect(page.getByText(/nao inventa data_referencia/i)).toBeVisible();
  const suffix = testInfo.project.name.includes("mobile") ? "agenda-list-mobile" : "agenda-list-desktop";
  await screenshotEvidence(page, suffix);
});

test("executa compromisso, lembrete e comunicacao idempotentes", async ({ page }, testInfo) => {
  await login(page, "ACME");
  await gotoAgenda(page);
  await page.getByLabel("Devedor").nth(1).fill("00000000-0000-4000-8000-000000000010");
  await page.getByLabel("Titulo").fill("Retorno criado");
  await page.getByLabel("Previsto para").fill("2026-08-14T15:00:00Z");
  await page.getByRole("button", { name: "Criar compromisso" }).click();
  await expect(page.getByText(/Compromisso idempotente registrado/)).toBeVisible();
  await page.getByPlaceholder("2026-08-14T16:00:00-03:00").first().fill("2026-08-14T16:00:00Z");
  await page.locator('input[name="mensagem"]').first().fill("Lembrete de retorno");
  await page.getByRole("button", { name: "Criar lembrete" }).first().click();
  await expect(page.getByText(/Lembrete idempotente registrado/)).toBeVisible();
  await page.getByLabel("Novo horario do compromisso").first().fill("2026-08-15T10:00:00Z");
  await page.getByRole("button", { name: "Reagendar", exact: true }).first().click();
  await expect(page.getByText(/Compromisso idempotente reagendado/)).toBeVisible();
  await page.getByRole("button", { name: "Concluir", exact: true }).first().click();
  await expect(page.getByText(/Compromisso idempotente atualizado/)).toBeVisible();
  await page.getByRole("button", { name: "Cancelar", exact: true }).first().click();
  await expect(page.getByText(/Compromisso idempotente atualizado/)).toBeVisible();
  await page.getByLabel("Novo horario do lembrete").fill("2026-08-15T09:00:00Z");
  await page.getByRole("button", { name: "Reagendar lembrete" }).click();
  await expect(page.getByText(/Lembrete idempotente reagendado/)).toBeVisible();
  await page.getByLabel("Motivo da conciliacao").fill("Conciliacao manual");
  await page.getByLabel("Provider message id").fill("provider-296");
  await page.getByLabel("Notification id").fill("00000000-0000-4000-8000-000000000084");
  await page.getByRole("button", { name: "Conciliar envio" }).click();
  await expect(page.getByText(/Lembrete idempotente conciliado/)).toBeVisible();
  await page.getByRole("button", { name: "Concluir lembrete" }).click();
  await expect(page.getByText(/Lembrete idempotente atualizado/)).toBeVisible();
  await page.getByRole("button", { name: "Cancelar lembrete" }).click();
  await expect(page.getByText(/Lembrete idempotente atualizado/)).toBeVisible();
  await page.getByLabel("Devedor").nth(2).fill("00000000-0000-4000-8000-000000000010");
  await page.getByLabel("Ocorrido em").fill("2026-08-14T16:30:00Z");
  await page.getByLabel("Resumo").fill("Contato pelo telefone");
  await page.getByLabel("Resultado").fill("Retorno confirmado");
  await page.getByRole("button", { name: "Registrar comunicacao" }).click();
  await expect(page.getByText(/Comunicacao idempotente registrada/)).toBeVisible();
  const suffix = testInfo.project.name.includes("mobile") ? "comunicacao-flow-mobile" : "agenda-command-desktop";
  await screenshotEvidence(page, suffix);
});

test("observa denied, empty, 404 e 5xx sem vazar detalhe backend", async ({ page }) => {
  await login(page, "nenhuma");
  await gotoAgenda(page);
  await expect(page.getByText("denied", { exact: true }).first()).toBeVisible();
  await login(page, "vazio");
  await gotoAgenda(page);
  await expect(page.getByText(/empty/).first()).toBeVisible();
  await login(page, "nao-encontrado");
  await gotoAgenda(page);
  await expect(page.getByRole("alert").first()).toContainText("Agenda ou comunicacao nao encontrada ou indisponivel.");
  await expect(page.getByText("detalhe cross-carteira")).toHaveCount(0);
  await login(page, "estados");
  await gotoAgenda(page);
  await expect(page.getByRole("alert").first()).toContainText("Servico temporariamente indisponivel.");
  await expect(page.getByText("stack secreta")).toHaveCount(0);
});
