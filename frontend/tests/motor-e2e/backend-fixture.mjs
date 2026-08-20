import { createServer } from "node:http";

const argument = process.argv.indexOf("--port");
const port = argument >= 0 ? Number(process.argv[argument + 1]) : 3206;
const id = (value) => `00000000-0000-4000-8000-${String(value).padStart(12, "0")}`;
const IDS = { tenant: id(1), user: id(2), wallet: id(3), profile: id(4), debtor: id(10), contract: id(30), loan: id(40), memory: id(50), installment: id(60), payment: id(70) };

function send(response, status, body, correlation = "corr-motor-294") {
  response.writeHead(status, { "Cache-Control": "no-store", "Content-Type": "application/json", "X-Correlation-ID": correlation });
  response.end(body === undefined ? undefined : JSON.stringify(body));
}

async function jsonBody(request) {
  const chunks = [];
  for await (const chunk of request) chunks.push(chunk);
  return JSON.parse(Buffer.concat(chunks).toString("utf8") || "{}");
}

function loginMode(body) {
  const email = String(body.email ?? "");
  const match = email.match(/\+([^@]+)/);
  return String(match?.[1] ?? body.identificador_institucional ?? "ACME").toLowerCase();
}
function modeFromAuthorization(request) {
  return String(request.headers.authorization ?? "").replace(/^Bearer access-/, "");
}

function permissions(mode) {
  if (mode === "nenhuma") return [];
  if (mode === "leitura") return ["motor.emprestimo.ler", "motor.parcela.ler", "motor.saldo.ler", "motor.memoria.ler", "motor.quitacao.executar"];
  // devedor.ler acompanha o Motor porque a lista identifica o Devedor pelo nome.
  // O modo "leitura" segue sem ela, para exercitar a degradacao do rotulo.
  return ["motor.emprestimo.criar", "motor.emprestimo.ler", "motor.parcela.gerar", "motor.parcela.ler", "motor.pagamento.registrar", "motor.saldo.ler", "motor.memoria.ler", "motor.quitacao.executar", "motor.renegociacao.criar", "devedor.ler"];
}

function operationalContext(mode) {
  const granted = permissions(mode);
  return {
    carteira_padrao: { id: IDS.wallet, nome: "Carteira Centro" },
    perfil: granted.length ? { id: IDS.profile, nome: "Operador Motor" } : null,
    permissoes: granted,
    tenant: { id: IDS.tenant, identificador_institucional: "ACME", nome: "Instituicao ACME" },
    usuario: { email: "operador@example.test", id: IDS.user, nome: "Operador Motor" },
  };
}

function memory(tipo = "saldo") {
  return {
    arredondamentos: ["Motor oficial"],
    criado_em: "2026-08-14T10:05:00Z",
    entradas: { origem: "contrato" },
    id: IDS.memory,
    passos: [{ arredondamento: null, entradas: { base: "1000.00" }, nome: "Leitura oficial", saidas: { total: "1010.00" } }],
    periodos: [],
    regra: { versao: "mvp" },
    resultados: { total: "1010.00" },
    tipo,
  };
}

function loan(overrides = {}) {
  return {
    carteira_id: IDS.wallet,
    contrato_id: IDS.contract,
    criado_em: "2026-08-14T10:00:00Z",
    devedor_id: IDS.debtor,
    estado: "ativo",
    id: IDS.loan,
    moeda: "BRL",
    parametros_financeiros: { origem: "contrato", canal: "motor" },
    principal_original: "1000.00",
    tenant_id: IDS.tenant,
    ...overrides,
  };
}

function installment() {
  return { encargos: "0.00", emprestimo_id: IDS.loan, estado: "prevista", id: IDS.installment, juros: "10.00", numero: 1, principal: "100.00", valor_liquidado: "0.00", valor_previsto: "110.00", vencimento: "2026-09-14" };
}

function payment() {
  return { chave_idempotencia: "idem-payment-294", emprestimo_id: IDS.loan, estado: "processado", id: IDS.payment, memoria: memory("pagamento"), parcelas_liquidadas: [IDS.installment], recebido_em: "2026-08-14T12:00:00Z", tenant_id: IDS.tenant, valor_amortizacao: "90.00", valor_encargos: "0.00", valor_juros: "10.00", valor_recebido: "100.00" };
}

function plan() {
  return { emprestimo_id: IDS.loan, memoria: memory("parcelas"), parcelas: [installment()], tenant_id: IDS.tenant };
}

const server = createServer(async (request, response) => {
  const url = new URL(request.url ?? "/", `http://127.0.0.1:${port}`);
  const correlation = String(request.headers["x-correlation-id"] ?? "corr-motor-294");
  if (request.method === "GET" && url.pathname === "/health") return send(response, 200, { checks: { database: "healthy" }, service: "api", status: "healthy" }, correlation);
  if (request.method === "POST" && url.pathname === "/auth/login") {
    const body = await jsonBody(request);
    const mode = loginMode(body);
    return send(response, 200, { access_token: `access-${mode === "acme" ? "acme" : mode}`, access_token_expira_em: "2099-08-14T12:15:00Z", refresh_token: `refresh-${mode}`, refresh_token_expira_em: "2099-08-21T12:00:00Z", tenant_id: IDS.tenant, token_type: "bearer", usuario_id: IDS.user }, correlation);
  }
  if (request.method === "POST" && url.pathname === "/auth/refresh") return send(response, 200, { access_token: "access-acme", access_token_expira_em: "2099-08-14T12:30:00Z", tenant_id: IDS.tenant, token_type: "bearer", usuario_id: IDS.user }, correlation);
  if (request.method === "POST" && url.pathname === "/auth/logout") { response.writeHead(204, { "X-Correlation-ID": correlation }); response.end(); return; }
  if (request.method === "GET" && url.pathname === "/iam/contexto-atual") return send(response, 200, operationalContext(modeFromAuthorization(request)), correlation);

  const mode = modeFromAuthorization(request);
  if (mode === "nenhuma") return send(response, 403, { codigo: "acesso_negado", mensagem: "Acesso negado." }, correlation);
  if (mode === "nao-encontrado") return send(response, 404, { codigo: "emprestimo_nao_encontrado", mensagem: "detalhe cross-carteira" }, correlation);
  if (mode === "estados") return send(response, 500, { codigo: "interno", mensagem: "stack secreta" }, "corr-motor-states-294");

  if (request.method === "GET" && url.pathname === `/credit/carteiras/${IDS.wallet}/devedores/${IDS.debtor}`) {
    // O painel do emprestimo abre com o nome do Devedor como titulo.
    return send(response, 200, { atualizado_em: "2026-08-14T10:00:00Z", carteira_id: IDS.wallet, contatos: [], criado_em: "2026-08-14T10:00:00Z", documento: "39053344705", estado: "ativo", id: IDS.debtor, nome: "Maria Souza", tenant_id: IDS.tenant }, correlation);
  }
  if (request.method === "GET" && url.pathname === `/credit/carteiras/${IDS.wallet}/devedores`) {
    // A lista resolve o nome do Devedor no servidor; sem esta rota a tela cairia
    // em "Devedor nao identificado" e a legibilidade nao seria provada.
    return send(response, 200, { items: [{ atualizado_em: "2026-08-14T10:00:00Z", carteira_id: IDS.wallet, contatos: [], criado_em: "2026-08-14T10:00:00Z", documento: "39053344705", estado: "ativo", id: IDS.debtor, nome: "Maria Souza", tenant_id: IDS.tenant }], page: 1, pages: 1, size: 100, total: 1 }, correlation);
  }
  if (request.method === "GET" && url.pathname === `/credit/carteiras/${IDS.wallet}/emprestimos`) {
    if (mode === "vazio") return send(response, 200, { items: [], page: 1, pages: 0, size: 20, total: 0 }, correlation);
    return send(response, 200, { items: [loan(), loan({ estado: "quitado", id: id(41), principal_original: "2500.00" })], page: 1, pages: 1, size: 20, total: 2 }, correlation);
  }
  if (request.method === "POST" && url.pathname === `/credit/contratos/${IDS.contract}/emprestimos`) return send(response, 201, loan(), correlation);
  if (request.method === "GET" && url.pathname === `/credit/emprestimos/${IDS.loan}`) return send(response, 200, loan(), correlation);
  if (request.method === "GET" && url.pathname === `/credit/emprestimos/${IDS.loan}/parcelas`) return send(response, 200, plan(), correlation);
  if (request.method === "POST" && url.pathname === `/credit/emprestimos/${IDS.loan}/parcelas`) return send(response, 200, plan(), correlation);
  if (request.method === "GET" && url.pathname === `/credit/emprestimos/${IDS.loan}/saldo`) return send(response, 200, { data_referencia: "2026-08-14", emprestimo_id: IDS.loan, encargos: "0.00", juros: "10.00", memoria: memory("saldo"), principal: "1000.00", tenant_id: IDS.tenant, total: "1010.00" }, correlation);
  if (request.method === "GET" && url.pathname === `/credit/emprestimos/${IDS.loan}/memoria-calculo`) return send(response, 200, [memory("saldo")], correlation);
  if (request.method === "GET" && url.pathname === `/credit/emprestimos/${IDS.loan}/quitacao`) return send(response, 200, { emprestimo_id: IDS.loan, memoria: memory("quitacao"), tenant_id: IDS.tenant, valor_quitacao: { componentes: { encargos: "0.00", juros: "10.00", principal: "1000.00" }, data_referencia: "2026-08-14", moeda: "BRL", valor_total: "1010.00" } }, correlation);
  if (request.method === "POST" && url.pathname === `/credit/emprestimos/${IDS.loan}/pagamentos`) return send(response, 200, payment(), correlation);
  if (request.method === "POST" && url.pathname === `/credit/emprestimos/${IDS.loan}/quitacao`) return send(response, 200, { emprestimo_id: IDS.loan, estado: "quitado", memoria_quitacao: memory("quitacao"), pagamento: payment(), tenant_id: IDS.tenant }, correlation);
  if (request.method === "POST" && url.pathname === `/credit/emprestimos/${IDS.loan}/renegociacoes`) return send(response, 409, { codigo: "conflito_estado", mensagem: "Renegociacao indisponivel no estado atual." }, correlation);
  return send(response, 404, { codigo: "emprestimo_nao_encontrado", mensagem: "Recurso indisponivel." }, correlation);
});

server.listen(port, "127.0.0.1");
for (const signal of ["SIGINT", "SIGTERM"]) process.on(signal, () => server.close(() => process.exit(0)));
