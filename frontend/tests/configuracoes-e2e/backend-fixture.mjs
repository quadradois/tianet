import { createServer } from "node:http";

const argument = process.argv.indexOf("--port");
const port = argument >= 0 ? Number(process.argv[argument + 1]) : 3210;
const id = (value) => `00000000-0000-4000-8000-${String(value).padStart(12, "0")}`;
const IDS = { calendar: id(101), config: id(100), modalidade: id(102), profile: id(4), tenant: id(1), user: id(2), wallet: id(3) };

function send(response, status, body, correlation = "corr-configuracoes-298") {
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
  return [
    "configuracoes_financeiras.configuracao.ler",
    "configuracoes_financeiras.configuracao.gerir",
    "configuracoes_financeiras.configuracao.aprovar",
    "configuracoes_financeiras.configuracao.ativar",
    "configuracoes_financeiras.modalidade.gerir",
    "configuracoes_financeiras.calendario.gerir",
    "configuracoes_financeiras.snapshot.capturar",
  ];
}

function context(mode) {
  const granted = permissions(mode);
  return {
    carteira_padrao: { id: IDS.wallet, nome: "Carteira Centro" },
    perfil: granted.length ? { id: IDS.profile, nome: "Operador Configuracoes" } : null,
    permissoes: granted,
    tenant: { id: IDS.tenant, identificador_institucional: "ACME", nome: "Instituicao ACME" },
    usuario: { email: "operador@example.test", id: IDS.user, nome: "Operador Configuracoes" },
    whatsapp: { numero: "556299999999", pareada: true },
  };
}

function configuracao(estado = "rascunho") {
  return {
    aprovada_em: null,
    aprovada_por_usuario_id: null,
    atualizada_em: null,
    calendario_id: IDS.calendar,
    carteira_id: IDS.wallet,
    criada_em: "2026-08-14T12:00:00Z",
    criada_por_usuario_id: IDS.user,
    estado,
    id: IDS.config,
    modalidade: "consignado",
    parametros: { limite: "opaco", memoria: ["sem-calculo-frontend"] },
    tenant_id: IDS.tenant,
    total_eventos: 3,
    versao: 1,
    vigencia_fim: null,
    vigencia_inicio: "2026-08-14",
  };
}

function modalidade() {
  return { ativa: true, carteira_id: IDS.wallet, codigo: "consignado", id: IDS.modalidade, nome: "Consignado", tenant_id: IDS.tenant };
}

function calendario() {
  return { carteira_id: IDS.wallet, codigo: "br", feriados: ["2026-01-01"], id: IDS.calendar, nome: "Brasil", tenant_id: IDS.tenant };
}

function snapshot() {
  return { capturado_em: "2026-08-14T12:00:00Z", capturado_por_usuario_id: IDS.user, carteira_id: IDS.wallet, configuracao_id: IDS.config, hash_parametros: "sha256:opaco", modalidade: "consignado", motivo: null, parametros: { limite: "opaco" }, tenant_id: IDS.tenant, versao: 1 };
}

const server = createServer(async (request, response) => {
  const url = new URL(request.url ?? "/", `http://127.0.0.1:${port}`);
  const correlation = String(request.headers["x-correlation-id"] ?? "corr-configuracoes-298");
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
  if (mode === "estados" && url.pathname === "/credit/configuracoes-financeiras") return send(response, 500, { codigo: "interno", mensagem: "stack secreta" }, "corr-config-states-298");
  if (mode === "nao-encontrado" && url.pathname === "/credit/configuracoes-financeiras") return send(response, 404, { codigo: "recurso_indisponivel", mensagem: "detalhe cross tenant" }, correlation);
  if (mode === "regra" && request.method === "POST") return send(response, 422, { codigo: "regra_violada", mensagem: "detalhe financeiro interno" }, correlation);

  if (request.method === "GET" && url.pathname === "/credit/configuracoes-financeiras") return send(response, 200, mode === "vazio" || mode === "estados" ? [] : [configuracao()], correlation);
  if (request.method === "GET" && url.pathname === "/credit/configuracoes-financeiras/vigente") return send(response, 200, { carteira_id: IDS.wallet, configuracao_id: IDS.config, consultada_em: "2026-08-14T12:00:00Z", modalidade: "consignado", parametros: { limite: "opaco" }, tenant_id: IDS.tenant, versao: 1 }, correlation);
  if (request.method === "GET" && url.pathname === "/credit/configuracoes-financeiras/modalidades") return send(response, 200, [modalidade()], correlation);
  if (request.method === "GET" && url.pathname === "/credit/configuracoes-financeiras/calendarios") return send(response, 200, [calendario()], correlation);
  if (request.method === "POST" && url.pathname === "/credit/configuracoes-financeiras/modalidades") return send(response, 201, modalidade(), correlation);
  if (request.method === "POST" && url.pathname === "/credit/configuracoes-financeiras/calendarios") return send(response, 201, calendario(), correlation);
  if (request.method === "POST" && url.pathname === "/credit/configuracoes-financeiras") return send(response, 201, configuracao(), correlation);
  if (request.method === "POST" && url.pathname.endsWith("/aprovar")) return send(response, 200, configuracao("aprovada"), correlation);
  if (request.method === "POST" && url.pathname.endsWith("/programar")) return send(response, 200, configuracao("programada"), correlation);
  if (request.method === "POST" && url.pathname.endsWith("/ativar")) return send(response, 200, configuracao("ativa"), correlation);
  if (request.method === "POST" && url.pathname.endsWith("/inativar")) return send(response, 200, configuracao("inativa"), correlation);
  if (request.method === "POST" && url.pathname === "/credit/configuracoes-financeiras/snapshots") return send(response, 200, snapshot(), correlation);
  return send(response, 404, { codigo: "recurso_indisponivel", mensagem: "Recurso indisponivel." }, correlation);
});

server.listen(port, "127.0.0.1");
for (const signal of ["SIGINT", "SIGTERM"]) process.on(signal, () => server.close(() => process.exit(0)));
