import { resolve } from "node:path";

import { expect, test, type Page } from "@playwright/test";

function emailForInstitution(institution: string): string {
  const mode = institution.toLowerCase();
  return mode === "acme" ? "operador@example.test" : `operador+${mode}@example.test`;
}
async function login(page: Page, institution = "ACME") {
  await page.goto("/login");
  await page.getByRole("textbox", { name: "E-mail" }).fill(emailForInstitution(institution));
  await page.getByLabel("Senha").fill("segredo-cobranca");
  await page.getByRole("button", { name: "Entrar" }).click();
  await expect(page).toHaveURL(/\/app(?:\?|$)/);
}

async function gotoCobranca(page: Page) {
  await page.goto("/app/cobranca");
  await expect(page.getByRole("heading", { name: "Fila de cobranca" })).toBeVisible();
}

test("renderiza fila de cobranca e captura desktop/mobile", async ({ page }, testInfo) => {
  await login(page, "ACME");
  await gotoCobranca(page);
  await expect(page.getByRole("heading", { name: "Caso oficial de cobranca" }).first()).toBeVisible();
  await expect(page.getByText("R$ 1.010,00").first()).toBeVisible();
  await expect(page.getByText(/Registre o contato feito/i).first()).toBeVisible();
  const suffix = testInfo.project.name.includes("mobile") ? "cobranca-list-mobile" : "cobranca-list-desktop";
  await page.screenshot({ animations: "disabled", caret: "initial", fullPage: false, path: resolve(`../docs/audits/evidence/frontend-mvp-imp-295-${suffix}.png`) });
});

test("executa acao, promessa e apropriacao idempotentes", async ({ page }, testInfo) => {
  await login(page, "ACME");
  await gotoCobranca(page);
  await page.getByLabel("Resultado").first().fill("Contato confirmado");
  await page.getByRole("button", { name: "Registrar acao" }).first().click();
  await expect(page.getByText(/Acao de cobranca registrada/)).toBeVisible();
  await page.getByLabel("Valor declarado").first().fill("100,00");
  await page.getByLabel("Data da promessa").first().fill("2026-08-21");
  await page.getByRole("button", { name: "Registrar promessa" }).first().click();
  await expect(page.getByText(/Promessa declaratoria registrada/)).toBeVisible();
  await page.getByLabel("Promessa", { exact: true }).first().fill("00000000-0000-4000-8000-000000000081");
  await page.getByLabel("Pagamento", { exact: true }).first().fill("00000000-0000-4000-8000-000000000082");
  await page.getByRole("button", { name: "Conciliar pagamento" }).first().click();
  await expect(page.getByText("Pagamento oficial apropriado a promessa.")).toBeVisible();
  const suffix = testInfo.project.name.includes("mobile") ? "cobranca-promessa-mobile" : "cobranca-action-desktop";
  await page.screenshot({ animations: "disabled", caret: "initial", fullPage: false, path: resolve(`../docs/audits/evidence/frontend-mvp-imp-295-${suffix}.png`) });
});

test("observa denied, empty, 404 e 5xx sem vazar detalhe backend", async ({ page }) => {
  await login(page, "nenhuma");
  await gotoCobranca(page);
  await expect(page.getByText("Sem permissao", { exact: true })).toBeVisible();
  await login(page, "vazio");
  await gotoCobranca(page);
  await expect(page.getByText(/Nenhum caso ativo encontrado/)).toBeVisible();
  await login(page, "nao-encontrado");
  await gotoCobranca(page);
  await expect(page.getByRole("alert").first()).toContainText("Caso de cobranca nao encontrado ou indisponivel.");
  await expect(page.getByText("detalhe cross-carteira")).toHaveCount(0);
  await login(page, "estados");
  await gotoCobranca(page);
  await expect(page.getByRole("alert").first()).toContainText("Servico temporariamente indisponivel.");
  await expect(page.getByText("stack secreta")).toHaveCount(0);
});
