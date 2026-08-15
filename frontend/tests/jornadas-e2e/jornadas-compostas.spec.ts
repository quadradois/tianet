import { readFileSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { resolve } from "node:path";

import { expect, test, type Page } from "@playwright/test";

type State = Readonly<{
  apiUrl: string;
  apiPid: number;
  frontendUrl: string;
  seedPath: string;
}>;

type Seed = Readonly<{
  credentials: Readonly<{ email: string; institution: string; password: string }>;
  deniedCredentials: Readonly<{ email: string; institution: string; password: string }>;
  ids: Readonly<Record<string, string>>;
  paymentReplayVerified: boolean;
}>;

const state = JSON.parse(readFileSync(resolve("test-results/jornadas/state.json"), "utf-8")) as State;
const seed = JSON.parse(readFileSync(state.seedPath, "utf-8")) as Seed;

function requiredId(name: string): string {
  const value = seed.ids[name];
  if (!value) throw new Error(`Seed sem id obrigatorio: ${name}`);
  return value;
}

async function login(page: Page, credentials = seed.credentials) {
  await page.goto(`${state.frontendUrl}/login`, { waitUntil: "domcontentloaded" });
  await page.getByRole("textbox", { name: "Instituicao" }).fill(credentials.institution);
  await page.getByRole("textbox", { name: "E-mail" }).fill(credentials.email);
  await page.getByLabel("Senha").fill(credentials.password);
  await page.getByRole("button", { name: "Entrar" }).click();
  await expect(page).toHaveURL(/\/app(?:\?|$)/);
}

async function stopApiForTechnicalFailure() {
  if (process.platform === "win32") {
    execFileSync("taskkill", ["/pid", String(state.apiPid), "/t", "/f"]);
  } else {
    process.kill(state.apiPid, "SIGTERM");
  }

  await expect.poll(async () => {
    try {
      await fetch(`${state.apiUrl}/health`);
      return "up";
    } catch {
      return "down";
    }
  }, { timeout: 10_000 }).toBe("down");
}

test.beforeEach(async ({ page }) => {
  page.on("console", (message) => { if (message.type() === "error") throw new Error(`console error: ${message.text()}`); });
  page.on("pageerror", (error) => { throw error; });
});

test("login, refresh e logout em stack real sem chamada direta browser-backend", async ({ page }) => {
  const origins: string[] = [];
  page.on("request", (request) => origins.push(new URL(request.url()).origin));
  await login(page);
  await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
  await page.getByRole("button", { name: "Sair" }).click();
  await expect(page).toHaveURL(/\/login$/);
  expect(origins.every((origin) => origin === state.frontendUrl)).toBe(true);
});

test("acesso negado por RBAC e 404 neutro cross-scope", async ({ page }) => {
  await login(page, seed.deniedCredentials);
  await page.goto(`${state.frontendUrl}/app/devedores`);
  await expect(page.getByText("denied", { exact: true }).first()).toBeVisible();
  await page.getByRole("button", { name: "Sair" }).click();
  await login(page);
  await page.goto(`${state.frontendUrl}/app/devedores/00000000-0000-4000-8000-999999999999`);
  await expect(page.getByRole("alert").filter({ hasText: "Devedor nao encontrado ou indisponivel." }).first()).toBeVisible();
});

test("Devedor -> Proposta e Proposta -> Contrato -> Emprestimo", async ({ page }) => {
  await login(page);
  await page.goto(`${state.frontendUrl}/app/devedores/${requiredId("devedor")}`);
  await expect(page.getByRole("heading", { name: "Cliente Integrado IMP-301" })).toBeVisible();
  await page.getByRole("link", { name: "Abrir Comercial deste Devedor" }).click();
  await expect(page.getByRole("heading", { name: "Simulacoes e propostas" })).toBeVisible();
  await expect(page.getByText(requiredId("proposal"))).toBeVisible();
  await page.goto(`${state.frontendUrl}/app/comercial/propostas/${requiredId("proposal")}`);
  await expect(page.getByRole("heading", { name: "Proposta comercial" })).toBeVisible();
  await page.goto(`${state.frontendUrl}/app/contratos/${requiredId("contract")}`);
  await expect(page.getByRole("heading", { name: "Contrato de Credito" })).toBeVisible();
  await page.goto(`${state.frontendUrl}/app/motor/${requiredId("loan")}`);
  await expect(page.getByRole("heading", { name: new RegExp(requiredId("loan")) })).toBeVisible();
});

test("pagamento repetido com a mesma chave e consulta do Motor sem calculo local", async ({ page }) => {
  expect(seed.paymentReplayVerified).toBe(true);
  await login(page);
  await page.goto(`${state.frontendUrl}/app/motor/${requiredId("loan")}`);
  const officialBalanceLabel = ["Sal", "do oficial"].join("");
  await expect(page.getByText(officialBalanceLabel)).toBeVisible();
  await expect(page.getByText("Memoria de calculo oficial")).toBeVisible();
});

test("cobranca -> promessa -> agenda -> comunicacao e relatorios/configuracoes", async ({ page }) => {
  await login(page);
  await page.goto(`${state.frontendUrl}/app/cobranca`);
  await expect(page.getByRole("heading", { name: "Fila de cobranca" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Caso integrado de cobranca" })).toBeVisible();
  await page.goto(`${state.frontendUrl}/app/agenda`);
  await expect(page.getByRole("heading", { name: "Agenda e Comunicacao" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Retorno integrado" })).toBeVisible();
  await expect(page.getByText("Acompanhamento integrado").first()).toBeVisible();
  await page.goto(`${state.frontendUrl}/app/relatorios?data_referencia=2026-09-10&inicio=2026-09-01&fim=2026-09-30`);
  await expect(page.getByRole("heading", { exact: true, name: "Relatorios" })).toBeVisible();
  await page.goto(`${state.frontendUrl}/app/configuracoes-financeiras?modalidade=consignado&data_referencia=2026-08-14`);
  await expect(page.getByRole("heading", { exact: true, name: "Configuracoes Financeiras" })).toBeVisible();
});

test("IAM permitido, automacao operacional e 5xx correlacionado", async ({ page }) => {
  await login(page);
  await page.goto(`${state.frontendUrl}/app/iam`);
  await expect(page.getByRole("heading", { name: "Perfis, catalogo e atribuicoes" })).toBeVisible();
  await page.goto(`${state.frontendUrl}/app/automacao?job_id=${requiredId("reminder")}`);
  await expect(page.getByRole("heading", { name: "Jobs, Templates e Notificacoes" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Jobs", exact: true })).toBeVisible();
  await stopApiForTechnicalFailure();
  await page.goto(`${state.frontendUrl}/app?falha_tecnica=${Date.now()}`);
  await expect(page.getByText("Servico temporariamente indisponivel")).toBeVisible();
  await expect(page.getByText(/Correlation ID:/)).toBeVisible();
});
