import { createServer } from "node:http";

const argument = process.argv.indexOf("--port");
const port = argument >= 0 ? Number(process.argv[argument + 1]) : 3204;
const id = (value) => `00000000-0000-4000-8000-${String(value).padStart(12, "0")}`;
const IDS = { tenant: id(1), user: id(2), wallet: id(3), profile: id(4), debtor: id(10), inactive: id(11), proposal: id(20), simulation: id(21) };

function send(response, status, body, correlation = "corr-comercial-292") {
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
  if (mode === "leitura") return ["devedor.ler", "comercial.proposta.ler"];
  return ["devedor.ler", "comercial.simulacao.criar", "comercial.proposta.criar", "comercial.proposta.ler", "comercial.proposta.decidir", "comercial.proposta.integrar"];
}

function operationalContext(mode) {
  const granted = permissions(mode);
  return {
    carteira_padrao: { id: IDS.wallet, nome: "Carteira Centro" },
    perfil: granted.length ? { id: IDS.profile, nome: "Operador Comercial" } : null,
    permissoes: granted,
    tenant: { id: IDS.tenant, identificador_institucional: "ACME", nome: "Instituicao ACME" },
    usuario: { email: "operador@example.test", id: IDS.user, nome: "Operador Comercial" },
  };
}

function debtor(overrides = {}) {
  return {
    atualizado_em: null,
    carteira_id: IDS.wallet,
    contatos: [{ preferencial: true, tipo: "email", valor: "cliente@example.test" }],
    criado_em: "2026-08-14T10:00:00Z",
    documento: "12345678909",
    estado: "ativo",
    id: IDS.debtor,
    nome: "Cliente Devedor Comercial",
    ...overrides,
  };
}

function devedorHistory() {
  return {
    devedor_id: IDS.debtor,
    eventos: [
      { acao: "criar.sucesso", criado_em: "2026-08-14T10:00:00Z", detalhes: "Cadastro inicial", status: "sucesso" },
    ],
  };
}

function proposal(overrides = {}) {
  return {
    aprovada_em: null,
    aprovada_por_usuario_id: null,
    atualizado_em: null,
    carteira_id: IDS.wallet,
    criada_por_usuario_id: IDS.user,
    criado_em: "2026-08-14T10:10:00Z",
    devedor_id: IDS.debtor,
    estado: "rascunho",
    id: IDS.proposal,
    parametros: { produto: "assistido", canal: "operacao-assistida" },
    simulacao_id: IDS.simulation,
    tenant_id: IDS.tenant,
    total_decisoes: 0,
    ...overrides,
  };
}

function list(mode) {
  if (mode === "vazio") return { items: [], page: 1, pages: 0, size: 20, total: 0 };
  const many = mode === "estados";
  return {
    items: Array.from({ length: many ? 14 : 2 }, (_, index) => proposal({
      estado: index === 0 ? "rascunho" : "aprovada",
      id: index === 0 ? IDS.proposal : id(200 + index),
      total_decisoes: index,
    })),
    page: 1,
    pages: 1,
    size: 20,
    total: many ? 14 : 2,
  };
}

const server = createServer(async (request, response) => {
  const url = new URL(request.url ?? "/", `http://127.0.0.1:${port}`);
  const correlation = String(request.headers["x-correlation-id"] ?? "corr-comercial-292");
  if (request.method === "GET" && url.pathname === "/health") return send(response, 200, { checks: { database: "healthy" }, service: "api", status: "healthy" }, correlation);
  if (request.method === "POST" && url.pathname === "/auth/login") {
    const body = await jsonBody(request);
    const mode = loginMode(body);
    return send(response, 200, { access_token: `access-${mode === "acme" ? "acme" : mode}`, access_token_expira_em: "2099-08-14T12:15:00Z", refresh_token: `refresh-${mode}`, refresh_token_expira_em: "2099-08-21T12:00:00Z", tenant_id: IDS.tenant, token_type: "bearer", usuario_id: IDS.user }, correlation);
  }
  if (request.method === "POST" && url.pathname === "/auth/refresh") return send(response, 200, { access_token: "access-acme", access_token_expira_em: "2099-08-14T12:30:00Z", tenant_id: IDS.tenant, token_type: "bearer", usuario_id: IDS.user }, correlation);
  if (request.method === "POST" && url.pathname === "/auth/logout") { response.writeHead(204, { "X-Correlation-ID": correlation }); response.end(); return; }
  if (request.method === "GET" && url.pathname === "/iam/contexto-atual") {
    const mode = modeFromAuthorization(request);
    if (mode === "old") return send(response, 401, { codigo: "autenticacao_recusada", mensagem: "Autenticacao recusada." }, correlation);
    return send(response, 200, operationalContext(mode), correlation);
  }
  const mode = modeFromAuthorization(request);
  if (mode === "nenhuma") return send(response, 403, { codigo: "acesso_negado", mensagem: "Acesso negado." }, correlation);
  if (mode === "nao-encontrado") return send(response, 404, { codigo: "proposta_nao_encontrada", mensagem: "detalhe cross-carteira" }, correlation);
  if (mode === "estados" && url.pathname.includes("/propostas-comerciais") && request.method === "GET") return send(response, 500, { codigo: "interno", mensagem: "stack secreta" }, "corr-comercial-states-292");
  if (request.method === "GET" && url.pathname === `/credit/carteiras/${IDS.wallet}/devedores/${IDS.debtor}/historico`) return send(response, 200, devedorHistory(), correlation);
  if (request.method === "GET" && url.pathname === `/credit/carteiras/${IDS.wallet}/devedores/${IDS.debtor}`) return send(response, 200, debtor(), correlation);
  if (request.method === "GET" && url.pathname === `/credit/carteiras/${IDS.wallet}/devedores/${IDS.inactive}`) return send(response, 200, debtor({ estado: "inativo", id: IDS.inactive, nome: "Cliente Inativo" }), correlation);
  if (request.method === "GET" && url.pathname === `/credit/carteiras/${IDS.wallet}/devedores`) return send(response, 200, { items: [debtor(), debtor({ estado: "inativo", id: IDS.inactive, nome: "Cliente Inativo" })], page: 1, pages: 1, size: 20, total: 2 }, correlation);
  if (url.pathname === `/credit/carteiras/${IDS.wallet}/devedores/${IDS.debtor}/propostas-comerciais` && request.method === "GET") return send(response, 200, list(mode), correlation);
  if (url.pathname === `/credit/simulacoes-comerciais/${IDS.simulation}` && request.method === "GET") return send(response, 200, { carteira_id: IDS.wallet, criada_por_usuario_id: IDS.user, criado_em: "2026-08-14T10:00:00Z", devedor_id: IDS.debtor, id: IDS.simulation, parametros: { produto: "assistido" }, tenant_id: IDS.tenant }, correlation);
  if (url.pathname === `/credit/carteiras/${IDS.wallet}/devedores/${IDS.debtor}/simulacoes-comerciais` && request.method === "POST") return send(response, 201, { carteira_id: IDS.wallet, criada_por_usuario_id: IDS.user, criado_em: "2026-08-14T10:00:00Z", devedor_id: IDS.debtor, id: IDS.simulation, parametros: { produto: "assistido" }, tenant_id: IDS.tenant }, correlation);
  if (url.pathname === `/credit/carteiras/${IDS.wallet}/devedores/${IDS.debtor}/propostas-comerciais` && request.method === "POST") return send(response, 201, proposal(), correlation);
  if (url.pathname === `/credit/propostas-comerciais/${IDS.proposal}` && request.method === "GET") return send(response, 200, proposal({ estado: mode === "aprovada" ? "aprovada" : "em_analise", total_decisoes: 1, aprovada_em: mode === "aprovada" ? "2026-08-14T11:00:00Z" : null, aprovada_por_usuario_id: mode === "aprovada" ? IDS.user : null }), correlation);
  if (url.pathname === `/credit/propostas-comerciais/${IDS.proposal}` && request.method === "PATCH") return send(response, 200, proposal(), correlation);
  if (url.pathname === `/credit/propostas-comerciais/${IDS.proposal}/contrato-logico` && request.method === "GET") return send(response, 200, { aprovada_em: "2026-08-14T11:00:00Z", aprovada_por_usuario_id: IDS.user, carteira_id: IDS.wallet, devedor_id: IDS.debtor, parametros_aprovados: { produto: "assistido" }, proposta_id: IDS.proposal, tenant_id: IDS.tenant }, correlation);
  if (url.pathname.endsWith("/enviar-para-analise") && request.method === "POST") return send(response, 200, proposal({ estado: "em_analise", total_decisoes: 1 }), correlation);
  if (url.pathname.endsWith("/aprovar") && request.method === "POST") return send(response, 200, proposal({ estado: "aprovada", total_decisoes: 2, aprovada_em: "2026-08-14T11:00:00Z", aprovada_por_usuario_id: IDS.user }), correlation);
  if (url.pathname.endsWith("/recusar") && request.method === "POST") return send(response, 200, proposal({ estado: "recusada", total_decisoes: 2 }), correlation);
  if (url.pathname.endsWith("/cancelar") && request.method === "POST") return send(response, 409, { codigo: "conflito_estado", mensagem: "Transicao invalida." }, correlation);
  if (url.pathname.endsWith("/expirar") && request.method === "POST") return send(response, 422, { codigo: "regra_violada", mensagem: "Regra comercial violada." }, correlation);
  return send(response, 404, { codigo: "proposta_nao_encontrada", mensagem: "Recurso indisponivel." }, correlation);
});

server.listen(port, "127.0.0.1");
for (const signal of ["SIGINT", "SIGTERM"]) process.on(signal, () => server.close(() => process.exit(0)));
