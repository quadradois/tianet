import { createServer } from "node:http";

const argument = process.argv.indexOf("--port");
const port = argument >= 0 ? Number(process.argv[argument + 1]) : 3205;
const id = (value) => `00000000-0000-4000-8000-${String(value).padStart(12, "0")}`;
const IDS = { tenant: id(1), user: id(2), wallet: id(3), profile: id(4), debtor: id(10), proposal: id(20), contract: id(30), event: id(31) };

function send(response, status, body, correlation = "corr-contratos-293") {
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
  if (mode === "leitura") return ["contratos.contrato.ler"];
  return ["contratos.contrato.criar", "contratos.contrato.ler", "contratos.contrato.assinar", "contratos.contrato.liberar", "contratos.contrato.encerrar", "comercial.proposta.ler", "comercial.proposta.integrar"];
}

function operationalContext(mode) {
  const granted = permissions(mode);
  return {
    carteira_padrao: { id: IDS.wallet, nome: "Carteira Centro" },
    perfil: granted.length ? { id: IDS.profile, nome: "Operador Contratos" } : null,
    permissoes: granted,
    tenant: { id: IDS.tenant, identificador_institucional: "ACME", nome: "Instituicao ACME" },
    usuario: { email: "operador@example.test", id: IDS.user, nome: "Operador Contratos" },
  };
}

function contract(overrides = {}) {
  return {
    assinado_em: null,
    assinado_por_usuario_id: null,
    atualizado_em: null,
    carteira_id: IDS.wallet,
    criado_em: "2026-08-14T10:00:00Z",
    criado_por_usuario_id: IDS.user,
    devedor_id: IDS.debtor,
    estado: "rascunho",
    formalizado_em: null,
    formalizado_por_usuario_id: null,
    id: IDS.contract,
    liberado_em: null,
    liberado_por_usuario_id: null,
    motivo_encerramento: null,
    parametros: { produto: "assistido", canal: "contratos" },
    proposta_comercial_id: IDS.proposal,
    tenant_id: IDS.tenant,
    total_eventos: 1,
    ...overrides,
  };
}

function list(mode) {
  if (mode === "vazio") return { items: [], page: 1, pages: 0, size: 20, total: 0 };
  return { items: [contract(), contract({ estado: "assinado", id: id(32), total_eventos: 3 })], page: 1, pages: 1, size: 20, total: 2 };
}

function history() {
  return [
    { contrato_id: IDS.contract, criado_em: "2026-08-14T10:05:00Z", estado_anterior: "rascunho", estado_posterior: "formalizado", id: IDS.event, motivo: null, tipo: "formalizar", usuario_id: IDS.user },
  ];
}

const server = createServer(async (request, response) => {
  const url = new URL(request.url ?? "/", `http://127.0.0.1:${port}`);
  const correlation = String(request.headers["x-correlation-id"] ?? "corr-contratos-293");
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
  if (mode === "nao-encontrado") return send(response, 404, { codigo: "contrato_nao_encontrado", mensagem: "detalhe cross-carteira" }, correlation);
  if (mode === "estados") return send(response, 500, { codigo: "interno", mensagem: "stack secreta" }, "corr-contratos-states-293");

  if (request.method === "GET" && url.pathname === `/credit/carteiras/${IDS.wallet}/contratos`) return send(response, 200, list(mode), correlation);
  if (request.method === "POST" && url.pathname === `/credit/carteiras/${IDS.wallet}/contratos`) return send(response, 201, contract({ estado: "formalizado", formalizado_em: "2026-08-14T10:05:00Z", formalizado_por_usuario_id: IDS.user }), correlation);
  if (request.method === "GET" && url.pathname === `/credit/contratos/${IDS.contract}`) return send(response, 200, contract({ estado: mode === "assinado" ? "assinado" : "rascunho" }), correlation);
  if (request.method === "GET" && url.pathname === `/credit/contratos/${IDS.contract}/historico`) return send(response, 200, history(), correlation);
  if (request.method === "POST" && url.pathname === `/credit/contratos/${IDS.contract}/assinar`) return send(response, 200, contract({ estado: "assinado", assinado_em: "2026-08-14T10:10:00Z", assinado_por_usuario_id: IDS.user }), correlation);
  if (request.method === "POST" && url.pathname === `/credit/contratos/${IDS.contract}/liberar-para-motor`) return send(response, 200, { contrato_id: IDS.contract, proposta_comercial_id: IDS.proposal, tenant_id: IDS.tenant, carteira_id: IDS.wallet, devedor_id: IDS.debtor, parametros_contratados: { produto: "assistido" }, liberado_por_usuario_id: IDS.user, liberado_em: "2026-08-14T10:20:00Z" }, correlation);
  if (request.method === "POST" && url.pathname === `/credit/contratos/${IDS.contract}/cancelar`) return send(response, 409, { codigo: "conflito_estado", mensagem: "Transicao invalida." }, correlation);
  if (request.method === "POST" && url.pathname === `/credit/contratos/${IDS.contract}/encerrar`) return send(response, 200, contract({ estado: "encerrado", motivo_encerramento: "Administrativo" }), correlation);
  return send(response, 404, { codigo: "contrato_nao_encontrado", mensagem: "Recurso indisponivel." }, correlation);
});

server.listen(port, "127.0.0.1");
for (const signal of ["SIGINT", "SIGTERM"]) process.on(signal, () => server.close(() => process.exit(0)));
