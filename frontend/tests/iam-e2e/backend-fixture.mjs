import { createServer } from "node:http";

const argument = process.argv.indexOf("--port");
const port = argument >= 0 ? Number(process.argv[argument + 1]) : 3211;
const id = (value) => `00000000-0000-4000-8000-${String(value).padStart(12, "0")}`;
const IDS = { profile: id(4), tenant: id(1), user: id(2), wallet: id(3), known: id(5) };

function send(response, status, body, correlation = "corr-iam-299") {
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
  return ["perfil.ler", "perfil.gerir"];
}

function context(mode) {
  const granted = permissions(mode);
  return {
    carteira_padrao: { id: IDS.wallet, nome: "Carteira Centro" },
    perfil: granted.length ? { id: IDS.profile, nome: "Administrador IAM" } : null,
    permissoes: granted,
    tenant: { id: IDS.tenant, identificador_institucional: "ACME", nome: "Instituicao ACME" },
    usuario: { email: "operador@example.test", id: IDS.user, nome: "Operador IAM" },
    whatsapp: { numero: "556299999999", pareada: true },
  };
}

function perfil(estado = "ativo") {
  return { estado, id: IDS.profile, nome: "Administrador IAM", permissoes: ["perfil.ler", "perfil.gerir"], tenant_id: IDS.tenant };
}

function catalogo() {
  return {
    itens: [
      { codigo: "perfil.ler", descricao: "Consultar Perfis e catalogo", grupo: "perfil" },
      { codigo: "perfil.gerir", descricao: "Gerir Perfis e atribuicoes", grupo: "perfil" },
      { codigo: "tenant.usuario.gerir", descricao: "Permissao fora do recorte associavel somente se backend permitir", grupo: "tenant" },
    ],
    versao: "2026-08",
  };
}

function efetivas() {
  return { perfil_id: IDS.profile, perfil_nome: "Administrador IAM", permissoes: ["perfil.ler", "perfil.gerir"], usuario_id: IDS.known };
}

const server = createServer(async (request, response) => {
  const url = new URL(request.url ?? "/", `http://127.0.0.1:${port}`);
  const correlation = String(request.headers["x-correlation-id"] ?? "corr-iam-299");
  if (request.method === "GET" && url.pathname === "/health") return send(response, 200, { checks: { database: "healthy" }, service: "api", status: "healthy" }, correlation);
  if (request.method === "POST" && url.pathname === "/auth/login") {
    const body = await jsonBody(request);
    const selected = loginMode(body);
    const mode = selected === "acme" ? "acme" : selected;
    return send(response, 200, { access_token: `access-${mode}`, access_token_expira_em: "2099-08-14T12:15:00Z", refresh_token: `refresh-${mode}`, refresh_token_expira_em: "2099-08-21T12:00:00Z", tenant_id: IDS.tenant, token_type: "bearer", usuario_id: IDS.user }, correlation);
  }
  if (request.method === "POST" && url.pathname === "/auth/refresh") return send(response, 200, { access_token: "access-acme", access_token_expira_em: "2099-08-14T12:30:00Z", tenant_id: IDS.tenant, token_type: "bearer", usuario_id: IDS.user }, correlation);
  if (request.method === "POST" && url.pathname === "/auth/logout") { response.writeHead(204, { "X-Correlation-ID": correlation }); response.end(); return; }
  if (request.method === "GET" && url.pathname === "/iam/contexto-atual") return send(response, 200, context(modeFromAuthorization(request)), correlation);

  const mode = modeFromAuthorization(request);
  if (mode === "nenhuma") return send(response, 403, { codigo: "acesso_negado", mensagem: "Acesso negado." }, correlation);
  if (mode === "estados" && url.pathname === "/iam/perfis") return send(response, 500, { codigo: "interno", mensagem: "stack segredo iam" }, "corr-iam-states-299");
  if (mode === "nao-encontrado") return send(response, 404, { codigo: "recurso_indisponivel", mensagem: "usuario interno" }, correlation);
  if (mode === "conflito" && request.method !== "GET") return send(response, 409, { codigo: "conflito_iam", mensagem: "detalhe interno" }, correlation);
  if (mode === "regra" && request.method !== "GET") return send(response, 422, { codigo: "regra_violada", mensagem: "detalhe interno" }, correlation);

  if (request.method === "GET" && url.pathname === "/iam/perfis") return send(response, 200, mode === "vazio" || mode === "estados" ? [] : [perfil()], correlation);
  if (request.method === "GET" && url.pathname === `/iam/perfis/${IDS.profile}`) return send(response, 200, perfil(), correlation);
  if (request.method === "GET" && url.pathname === "/iam/permissoes") return send(response, 200, catalogo(), correlation);
  if (request.method === "GET" && url.pathname === `/iam/usuarios/${IDS.known}/permissoes`) return send(response, 200, efetivas(), correlation);
  if (request.method === "POST" && url.pathname === "/iam/perfis") return send(response, 201, perfil(), correlation);
  if (request.method === "PATCH" && url.pathname === `/iam/perfis/${IDS.profile}`) return send(response, 200, perfil(), correlation);
  if (request.method === "POST" && url.pathname === `/iam/perfis/${IDS.profile}/inativar`) return send(response, 200, perfil("inativo"), correlation);
  if (request.method === "PUT" && url.pathname === `/iam/perfis/${IDS.profile}/permissoes/perfil.ler`) return send(response, 200, perfil(), correlation);
  if (request.method === "DELETE" && url.pathname === `/iam/perfis/${IDS.profile}/permissoes/perfil.ler`) return send(response, 200, perfil(), correlation);
  if (request.method === "PUT" && url.pathname === `/iam/usuarios/${IDS.known}/perfil/${IDS.profile}`) return send(response, 200, efetivas(), correlation);
  if (request.method === "DELETE" && url.pathname === `/iam/usuarios/${IDS.known}/perfil`) return send(response, 200, { ...efetivas(), perfil_id: null, perfil_nome: null, permissoes: [] }, correlation);
  return send(response, 404, { codigo: "recurso_indisponivel", mensagem: "Recurso indisponivel." }, correlation);
});

server.listen(port, "127.0.0.1");
for (const signal of ["SIGINT", "SIGTERM"]) process.on(signal, () => server.close(() => process.exit(0)));
