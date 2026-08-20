import { createServer } from "node:http";

const argument = process.argv.indexOf("--port");
const port = argument >= 0 ? Number(process.argv[argument + 1]) : 3207;
const id = (value) => `00000000-0000-4000-8000-${String(value).padStart(12, "0")}`;
const IDS = { action: id(83), appropriation: id(84), case: id(80), debtor: id(10), installment: id(85), loan: id(40), payment: id(82), profile: id(4), promise: id(81), tenant: id(1), user: id(2), wallet: id(3) };

function send(response, status, body, correlation = "corr-cobranca-295") {
  response.writeHead(status, { "Cache-Control": "no-store", "Content-Type": "application/json", "X-Correlation-ID": correlation });
  response.end(body === undefined ? undefined : JSON.stringify(body));
}

async function jsonBody(request) {
  const chunks = [];
  for await (const chunk of request) chunks.push(chunk);
  return JSON.parse(Buffer.concat(chunks).toString("utf8") || "{}");
}

function modeFromAuthorization(request) {
  return String(request.headers.authorization ?? "").replace(/^Bearer access-/, "");
}

function permissions(mode) {
  if (mode === "nenhuma") return [];
  if (mode === "leitura") return ["cobranca.caso.ler"];
  return ["cobranca.caso.ler", "cobranca.acao.registrar", "cobranca.promessa.registrar", "cobranca.promessa.apropriar"];
}

function operationalContext(mode) {
  const granted = permissions(mode);
  return {
    carteira_padrao: { id: IDS.wallet, nome: "Carteira Centro" },
    perfil: granted.length ? { id: IDS.profile, nome: "Operador Cobranca" } : null,
    permissoes: granted,
    tenant: { id: IDS.tenant, identificador_institucional: "ACME", nome: "Instituicao ACME" },
    usuario: { email: "operador@example.test", id: IDS.user, nome: "Operador Cobranca" },
  };
}

function chargeCase(overrides = {}) {
  return { carteira_id: IDS.wallet, caso_id: IDS.case, criado_em: "2026-08-14T10:00:00Z", devedor_id: IDS.debtor, emprestimo_id: IDS.loan, estado: "pendente", origem: "motor", tenant_id: IDS.tenant, titulo: "Caso oficial de cobranca", total_pendente: "1010.00", ...overrides };
}

function action() {
  return { acao_id: IDS.action, carteira_id: IDS.wallet, caso_id: IDS.case, devedor_id: IDS.debtor, emprestimo_id: IDS.loan, registrada_em: "2026-08-14T12:00:00Z", resultado: "Contato registrado", tenant_id: IDS.tenant, tipo: "contato", usuario_id: IDS.user };
}

function promise() {
  return { carteira_id: IDS.wallet, data_promessa: "2026-08-21", devedor_id: IDS.debtor, emprestimo_id: IDS.loan, estado: "pendente", promessa_id: IDS.promise, tenant_id: IDS.tenant, valor_declarado: "100.00" };
}

function appropriation() {
  return { apropriacao_id: IDS.appropriation, estado_promessa: "cumprida", pagamento_id: IDS.payment, promessa_id: IDS.promise, realizado_em: "2026-08-14T12:00:00Z", valor: "100.00" };
}

const server = createServer(async (request, response) => {
  const url = new URL(request.url ?? "/", `http://127.0.0.1:${port}`);
  const correlation = String(request.headers["x-correlation-id"] ?? "corr-cobranca-295");
  if (request.method === "GET" && url.pathname === "/health") return send(response, 200, { checks: { database: "healthy" }, service: "api", status: "healthy" }, correlation);
  if (request.method === "POST" && url.pathname === "/auth/login") {
    const body = await jsonBody(request);
    const mode = String(body.identificador_institucional ?? "ACME").toLowerCase();
    return send(response, 200, { access_token: `access-${mode === "acme" ? "acme" : mode}`, access_token_expira_em: "2099-08-14T12:15:00Z", refresh_token: `refresh-${mode}`, refresh_token_expira_em: "2099-08-21T12:00:00Z", tenant_id: IDS.tenant, token_type: "bearer", usuario_id: IDS.user }, correlation);
  }
  if (request.method === "POST" && url.pathname === "/auth/refresh") return send(response, 200, { access_token: "access-acme", access_token_expira_em: "2099-08-14T12:30:00Z", tenant_id: IDS.tenant, token_type: "bearer", usuario_id: IDS.user }, correlation);
  if (request.method === "POST" && url.pathname === "/auth/logout") { response.writeHead(204, { "X-Correlation-ID": correlation }); response.end(); return; }
  if (request.method === "GET" && url.pathname === "/iam/contexto-atual") return send(response, 200, operationalContext(modeFromAuthorization(request)), correlation);

  const mode = modeFromAuthorization(request);
  if (mode === "nenhuma") return send(response, 403, { codigo: "acesso_negado", mensagem: "Acesso negado." }, correlation);
  if (mode === "nao-encontrado") return send(response, 404, { codigo: "caso_nao_encontrado", mensagem: "detalhe cross-carteira" }, correlation);
  if (mode === "estados") return send(response, 500, { codigo: "interno", mensagem: "stack secreta" }, "corr-cobranca-states-295");

  if (request.method === "GET" && url.pathname === "/credit/cobrancas/casos") {
    if (mode === "vazio") return send(response, 200, { items: [], total: 0 }, correlation);
    return send(response, 200, { items: [chargeCase(), chargeCase({ caso_id: id(86), estado: "em_andamento", titulo: "Caso em andamento", total_pendente: "2500.00" })], total: 2 }, correlation);
  }
  if (request.method === "POST" && url.pathname === `/credit/cobrancas/casos/${IDS.case}/acoes`) return send(response, 200, action(), correlation);
  if (request.method === "POST" && url.pathname === `/credit/cobrancas/casos/${IDS.case}/promessas`) return send(response, 200, promise(), correlation);
  if (request.method === "POST" && url.pathname === `/credit/cobrancas/promessas/${IDS.promise}/apropriacoes`) return send(response, 200, appropriation(), correlation);
  return send(response, 404, { codigo: "caso_nao_encontrado", mensagem: "Recurso indisponivel." }, correlation);
});

server.listen(port, "127.0.0.1");
for (const signal of ["SIGINT", "SIGTERM"]) process.on(signal, () => server.close(() => process.exit(0)));
