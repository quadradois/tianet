import { createServer } from "node:http";

const argument = process.argv.indexOf("--port");
const port = argument >= 0 ? Number(process.argv[argument + 1]) : 3203;
const id = (value) => `00000000-0000-4000-8000-${String(value).padStart(12, "0")}`;
const IDS = { tenant: id(1), user: id(2), wallet: id(3), profile: id(4), debtor: id(10), inactive: id(11) };

function send(response, status, body, correlation = "corr-devedores-291") {
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
  if (mode === "leitura") return ["devedor.ler"];
  // motor.emprestimo.ler acompanha o Credor real: o detalhe do Devedor embute os
  // emprestimos dele. O modo "leitura" segue sem ela, para exercitar a negativa.
  return ["devedor.ler", "devedor.criar", "devedor.atualizar", "devedor.inativar", "devedor.reativar", "motor.emprestimo.ler"];
}

function loan(overrides = {}) {
  return {
    carteira_id: IDS.wallet,
    contrato_id: id(30),
    criado_em: "2026-08-14T10:00:00Z",
    devedor_id: IDS.debtor,
    estado: "ativo",
    id: id(40),
    moeda: "BRL",
    parametros_financeiros: { origem: "contrato" },
    principal_original: "1000.00",
    tenant_id: IDS.tenant,
    ...overrides,
  };
}

function operationalContext(mode) {
  const granted = permissions(mode);
  return {
    carteira_padrao: { id: IDS.wallet, nome: "Carteira Centro" },
    perfil: granted.length ? { id: IDS.profile, nome: "Operador" } : null,
    permissoes: granted,
    tenant: { id: IDS.tenant, identificador_institucional: "ACME", nome: "Instituicao ACME" },
    usuario: { email: "operador@example.test", id: IDS.user, nome: "Operador Devedores" },
    whatsapp: { numero: "556299999999", pareada: true },
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
    nome: "Cliente Devedor",
    ...overrides,
  };
}

function list(empty = false, many = false) {
  if (empty) return { items: [], page: 1, pages: 0, size: 20, total: 0 };
  const size = many ? 18 : 2;
  return {
    items: Array.from({ length: size }, (_, index) => debtor({
      documento: `1234567890${index}`,
      id: index === 0 ? IDS.debtor : id(100 + index),
      nome: `Cliente Devedor ${index + 1} com nome extenso para overflow`,
    })),
    page: 1,
    pages: 1,
    size: 20,
    total: size,
  };
}

function history() {
  return {
    devedor_id: IDS.debtor,
    eventos: [
      { acao: "criar.sucesso", criado_em: "2026-08-14T10:00:00Z", detalhes: "Cadastro inicial", status: "sucesso" },
      { acao: "atualizar.sucesso", criado_em: "2026-08-14T11:00:00Z", detalhes: null, status: "sucesso" },
    ],
  };
}

const server = createServer(async (request, response) => {
  const url = new URL(request.url ?? "/", `http://127.0.0.1:${port}`);
  const correlation = String(request.headers["x-correlation-id"] ?? "corr-devedores-291");
  if (request.method === "GET" && url.pathname === "/health") return send(response, 200, { checks: { database: "healthy" }, service: "api", status: "healthy" }, correlation);
  if (request.method === "POST" && url.pathname === "/auth/login") {
    const body = await jsonBody(request);
    const selected = loginMode(body);
    const mode = selected === "expirado" ? "old" : selected === "acme" ? "acme" : selected;
    return send(response, 200, { access_token: `access-${mode}`, access_token_expira_em: "2099-08-14T12:15:00Z", refresh_token: `refresh-${mode}`, refresh_token_expira_em: "2099-08-21T12:00:00Z", tenant_id: IDS.tenant, token_type: "bearer", usuario_id: IDS.user }, correlation);
  }
  if (request.method === "POST" && url.pathname === "/auth/refresh") return send(response, 200, { access_token: "access-acme", access_token_expira_em: "2099-08-14T12:30:00Z", tenant_id: IDS.tenant, token_type: "bearer", usuario_id: IDS.user }, correlation);
  if (request.method === "POST" && url.pathname === "/auth/logout") { response.writeHead(204, { "X-Correlation-ID": correlation }); response.end(); return; }
  if (request.method === "GET" && url.pathname === "/iam/contexto-atual") {
    const mode = modeFromAuthorization(request);
    if (mode === "old") return send(response, 401, { codigo: "autenticacao_recusada", mensagem: "Autenticacao recusada." }, correlation);
    return send(response, 200, operationalContext(mode), correlation);
  }
  const mode = modeFromAuthorization(request);
  if (mode === "lento") await new Promise((resolve) => setTimeout(resolve, 350));
  if (request.method === "GET" && url.pathname === `/credit/carteiras/${IDS.wallet}/emprestimos`) {
    if (mode === "vazio") return send(response, 200, { items: [], page: 1, pages: 0, size: 100, total: 0 }, correlation);
    return send(response, 200, { items: [loan(), loan({ estado: "quitado", id: id(41), principal_original: "2500.00" })], page: 1, pages: 1, size: 100, total: 2 }, correlation);
  }
  if (!url.pathname.startsWith(`/credit/carteiras/${IDS.wallet}/devedores`)) {
    return send(response, 404, { codigo: "devedor_nao_encontrado", mensagem: "detalhe cross-carteira" }, correlation);
  }
  if (mode === "estados" && request.method === "GET" && url.pathname.endsWith("/devedores")) return send(response, 500, { codigo: "interno", mensagem: "stack secreta" }, "corr-devedores-states-291");
  if (mode === "nao-encontrado") return send(response, 404, { codigo: "devedor_nao_encontrado", mensagem: "detalhe cross-carteira" }, correlation);
  if (request.method !== "GET" && !request.headers["idempotency-key"]) return send(response, 400, { codigo: "idempotencia_ausente", mensagem: "Idempotency-Key obrigatoria." }, correlation);
  if (request.method === "GET" && url.pathname.endsWith("/historico")) return send(response, 200, history(), correlation);
  if (request.method === "GET" && url.pathname.endsWith(`/${IDS.debtor}`)) return send(response, 200, debtor(), correlation);
  if (request.method === "GET" && url.pathname.endsWith("/devedores")) {
    if (url.searchParams.get("documento")) return send(response, 200, debtor(), correlation);
    return send(response, 200, list(mode === "vazio", mode === "estados"), correlation);
  }
  if (request.method === "POST" && url.pathname.endsWith("/devedores")) {
    const body = await jsonBody(request);
    if (body.documento === "duplicado") return send(response, 409, { codigo: "devedor_ja_existe", mensagem: "Documento duplicado." }, correlation);
    return send(response, 201, debtor({ documento: body.documento, nome: body.nome }), correlation);
  }
  if (request.method === "PATCH" && url.pathname.endsWith(`/${IDS.debtor}`)) {
    const body = await jsonBody(request);
    if (body.nome === "x") return send(response, 422, { codigo: "regra_violada", mensagem: "Nome invalido." }, correlation);
    return send(response, 200, debtor({ nome: body.nome ?? "Cliente Devedor" }), correlation);
  }
  if (request.method === "POST" && url.pathname.endsWith("/inativar")) return send(response, 200, debtor({ estado: "inativo", id: IDS.inactive }), correlation);
  if (request.method === "POST" && url.pathname.endsWith("/reativar")) return send(response, 200, debtor({ estado: "ativo", id: IDS.inactive }), correlation);
  return send(response, 404, { codigo: "devedor_nao_encontrado", mensagem: "Recurso indisponivel." }, correlation);
});

server.listen(port, "127.0.0.1");
for (const signal of ["SIGINT", "SIGTERM"]) process.on(signal, () => server.close(() => process.exit(0)));
