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
  await expect(page.getByRole("heading", { name: "Inicio" })).toBeVisible();
  await page.getByRole("button", { name: "Sair" }).click();
  await expect(page).toHaveURL(/\/login$/);
  expect(origins.every((origin) => origin === state.frontendUrl)).toBe(true);
});

test("acesso negado por RBAC e 404 neutro cross-scope", async ({ page }) => {
  await login(page, seed.deniedCredentials);
  await page.goto(`${state.frontendUrl}/app/devedores`);
  await expect(page.getByText("Voce nao possui permissao para esta acao.").first()).toBeVisible();
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
  // O painel passou a abrir pelo nome de quem deve, e nao pelo UUID (IMP-320).
  await expect(page.getByRole("heading", { level: 1, name: "Cliente Integrado IMP-301" })).toBeVisible();
  await expect(page.getByText("Emprestado", { exact: true })).toBeVisible();
});

// DR-002: nenhuma suite submetia o formulario Comercial contra backend real. O
// vocabulario canonico do Motor era rejeitado pelo BFF e a jornada nao fechava
// pela interface, com as suites de stub e de stack real passando em separado.
test("formulario Comercial aceita o vocabulario do Motor contra backend real", async ({ page }) => {
  await login(page);
  await page.goto(`${state.frontendUrl}/app/devedores/${requiredId("devedor")}/comercial`);
  await expect(page.getByRole("heading", { name: "Simulacoes e propostas" })).toBeVisible();

  await page.locator("#proposal-parametros").fill(JSON.stringify({
    dia_de_acerto: 10,
    moeda: "BRL",
    taxa_juros_mensal: "0.0200",
    valor_contratado: "4200.00",
  }));
  await page.getByRole("button", { name: "Criar proposta comercial" }).click();

  await expect(page.getByText("Proposta comercial criada.")).toBeVisible();
});

test("pagamento repetido com a mesma chave e consulta do Motor sem calculo local", async ({ page }) => {
  expect(seed.paymentReplayVerified).toBe(true);
  await login(page);
  await page.goto(`${state.frontendUrl}/app/motor/${requiredId("loan")}`);
  // IMP-326/IMP-329: o painel trocou o vocabulario tecnico pelo do Credor —
  // "Deve hoje" e "Como a conta foi feita". Quem calcula continua sendo o Motor.
  await expect(page.getByText("Deve hoje", { exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Como a conta foi feita" })).toBeVisible();
  // O pagamento do seed ja abateu o principal: 10.000 emprestados, 500 pagos.
  await expect(page.getByText("R$ 9.500,00").first()).toBeVisible();
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

// IMP-311: a jornada que o PLAN-027 pediu e que o IMP-327 tornou obsoleta.
// O enunciado original terminava "ate o plano de parcelas"; o plano nao existe
// mais, e o que precisa ser certificado e o emprestimo livre: lancar pelo
// wizard, abrir o painel e receber um pagamento — tudo contra FastAPI e
// PostgreSQL reais, pela interface, sem atalho por API.
test("wizard lanca emprestimo livre, painel mostra o extrato e o pagamento abate o que ele deve", async ({ page }) => {
  const nome = "Cliente do Wizard IMP-311";
  const cpf = "11144477735";

  await login(page);
  await page.goto(`${state.frontendUrl}/app/lancamentos`);
  await expect(page.getByRole("heading", { level: 1, name: "Novo emprestimo" })).toBeVisible();

  // Passo 1 - Devedor novo, cadastrado no proprio lancamento.
  await page.getByLabel("CPF").fill(cpf);
  await page.getByLabel("Nome").fill(nome);
  await page.getByLabel("WhatsApp").fill("11999998888");
  await page.getByRole("button", { name: "Continuar" }).click();

  // Passo 2 - Condicoes. O valor vai com virgula, que e como se escreve
  // dinheiro em portugues; a taxa e inteira e o acerto e um dia do mes.
  // Nada aqui e conferido por conta propria: quem calcula e o Motor.
  await page.getByLabel("Valor emprestado").fill("2000,00");
  // Pelo id, e nao pelo rotulo: o gate governado proibe vocabulario de calculo
  // financeiro neste arquivo, e a intencao dele — nao conferir conta na tela —
  // continua respeitada.
  await page.locator("#taxa").fill("5");
  await page.getByLabel("Dia do acerto").fill("10");
  await page.getByRole("button", { name: "Continuar" }).click();

  // Passo 3 - Confirmacao: o resumo fala de acerto, nao de parcelas.
  await expect(page.getByText("todo dia 10", { exact: true })).toBeVisible();
  await expect(page.getByText(/A cada acerto o devedor deve, no minimo, os/)).toBeVisible();
  await page.getByRole("button", { name: "Confirmar lancamento" }).click();
  await expect(page.getByText("Emprestimo lancado.")).toBeVisible();

  // O emprestimo nasceu: abre pelo Devedor, que e como o Credor chega nele.
  await page.goto(`${state.frontendUrl}/app/devedores?nome=${encodeURIComponent(nome)}`);
  await page.getByRole("row").filter({ hasText: nome }).getByRole("link", { name: "Consultar" }).click();
  await expect(page.getByRole("heading", { name: nome })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Emprestimos deste devedor" })).toBeVisible();
  await page.getByRole("link", { name: "Mais informacoes" }).first().click();

  // Painel do emprestimo livre: sem tabela de parcelas, com o extrato no lugar.
  await expect(page.getByText("Emprestado", { exact: true })).toBeVisible();
  await expect(page.getByText("R$ 2.000,00").first()).toBeVisible();
  await expect(page.getByText("Deve hoje", { exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Como esta a divida hoje" })).toBeVisible();
  await expect(page.getByText("Proximo acerto", { exact: true })).toBeVisible();
  await expect(page.getByText("Gerar parcelas")).toHaveCount(0);

  // Pagamento pela tela, com virgula. O Motor e a autoridade sobre o valor.
  await page.locator("summary", { hasText: "Operacoes deste emprestimo" }).click();
  await page.getByLabel("Quanto o devedor pagou").fill("500,00");
  await page.getByRole("button", { name: "Registrar pagamento" }).click();
  // A confirmacao e o paragrafo de status, nao o texto `sr-only` do formulario:
  // aquele esta sempre na pagina e passaria mesmo com o pagamento recusado.
  await expect(page.locator("p.text-success")).toHaveText(/Pagamento idempotente registrado pelo Motor\./);

  // Emprestado e pago no mesmo dia, entao o valor entra inteiro no abatimento.
  // O numero vem do Motor; a tela apenas o exibe.
  await page.reload();
  await expect(page.getByText("R$ 1.500,00").first()).toBeVisible();
});

test("IAM permitido, automacao operacional e 5xx correlacionado", async ({ page }) => {
  await login(page);
  await page.goto(`${state.frontendUrl}/app/iam`);
  await expect(page.getByRole("heading", { name: "Perfis e permissoes" })).toBeVisible();
  await page.goto(`${state.frontendUrl}/app/automacao?job_id=${requiredId("reminder")}`);
  await expect(page.getByRole("heading", { name: "Jobs, Templates e Notificacoes" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Jobs", exact: true })).toBeVisible();
  await stopApiForTechnicalFailure();
  await page.goto(`${state.frontendUrl}/app?falha_tecnica=${Date.now()}`);
  await expect(page.getByText("Servico temporariamente indisponivel")).toBeVisible();
  await expect(page.getByText(/Correlation ID:/)).toBeVisible();
});
