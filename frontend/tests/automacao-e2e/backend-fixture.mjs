import { createServer } from "node:http";

const argument = process.argv.indexOf("--port");
const port = argument >= 0 ? Number(process.argv[argument + 1]) : 3212;
const id = (value) => `00000000-0000-4000-8000-${String(value).padStart(12, "0")}`;
const IDS = { job: id(81), notification: id(82), template: id(83), reminder: id(84), profile: id(4), tenant: id(1), user: id(2), wallet: id(3) };

function send(response, status, body, correlation = "corr-automacao-300") {
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
  return ["automacao.job.consultar", "automacao.job.cancelar", "automacao.job.retry", "notificacao.consultar", "notificacao.template.gerir", "notificacao.conciliar"];
}

function context(mode) {
  const granted = permissions(mode);
  return {
    carteira_padrao: { id: IDS.wallet, nome: "Carteira Centro" },
    perfil: granted.length ? { id: IDS.profile, nome: "Operador Automacao" } : null,
    permissoes: granted,
    tenant: { id: IDS.tenant, identificador_institucional: "ACME", nome: "Instituicao ACME" },
    usuario: { email: "operador@example.test", id: IDS.user, nome: "Operador Automacao" },
    whatsapp: { numero: "556299999999", pareada: true },
  };
}

function job() {
  return { cancelamento_solicitado: false, carteira_id: IDS.wallet, correlation_id: "corr-job-official", estado: "agendado", executar_em: "2026-08-14T15:00:00Z", id: IDS.job, max_tentativas: 3, origem_id: IDS.reminder, origem_tipo: "lembrete", proxima_execucao_em: null, tentativas: 0, tipo: "notificacao" };
}

function notification(estado = "resultado_desconhecido") {
  return { carteira_id: IDS.wallet, codigo_resultado: null, estado, id: IDS.notification, job_id: IDS.job, lembrete_id: IDS.reminder, provider_message_id: "provider-ok", resultado_em: null };
}

function template(estado = "rascunho") {
  return { aprovado_em: estado === "aprovado" || estado === "ativo" ? "2026-08-14T15:20:00Z" : null, ativado_em: estado === "ativo" ? "2026-08-14T15:30:00Z" : null, codigo: "cobranca-lembrete", estado, hash_conteudo: "hash-template", id: IDS.template, versao: 1 };
}

function page(items) {
  return { items, page: 1, pages: 1, size: 20, total: items.length };
}

const server = createServer(async (request, response) => {
  const url = new URL(request.url ?? "/", `http://127.0.0.1:${port}`);
  const correlation = String(request.headers["x-correlation-id"] ?? "corr-automacao-300");
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
  if (mode === "nao-encontrado") return send(response, 404, { codigo: "recurso_indisponivel", mensagem: "detalhe interno" }, correlation);
  if (mode === "conflito" && request.method === "POST") return send(response, 409, { codigo: "conflito_estado", mensagem: "stack segredo" }, correlation);
  if (mode === "regra" && request.method === "POST") return send(response, 422, { codigo: "regra_violada", mensagem: "stack segredo" }, correlation);
  if (mode === "estados" && url.pathname === "/credit/automacao/jobs") return send(response, 500, { codigo: "interno", mensagem: "stack segredo automacao" }, "corr-auto-states-300");
  if (mode === "vazio") {
    if (url.pathname === "/credit/automacao/jobs") return send(response, 200, page([]), correlation);
    if (url.pathname === "/credit/notificacoes") return send(response, 200, page([]), correlation);
    if (url.pathname === "/credit/notificacoes/templates") return send(response, 200, page([]), correlation);
  }

  if (request.method === "GET" && url.pathname === "/credit/automacao/jobs") return send(response, 200, page([job()]), correlation);
  if (request.method === "GET" && url.pathname === `/credit/automacao/jobs/${IDS.job}`) return send(response, 200, job(), correlation);
  if (request.method === "POST" && url.pathname === `/credit/automacao/jobs/${IDS.job}/cancelar`) return send(response, 202, { ...job(), cancelamento_solicitado: true }, correlation);
  if (request.method === "POST" && url.pathname === `/credit/automacao/jobs/${IDS.job}/retry`) return send(response, 202, { ...job(), tentativas: 1 }, correlation);
  if (request.method === "GET" && url.pathname === "/credit/notificacoes") return send(response, 200, page([notification()]), correlation);
  if (request.method === "GET" && url.pathname === `/credit/notificacoes/${IDS.notification}`) return send(response, 200, notification(), correlation);
  if (request.method === "GET" && url.pathname === "/credit/notificacoes/templates") return send(response, 200, page([template()]), correlation);
  if (request.method === "POST" && url.pathname === "/credit/notificacoes/templates") return send(response, 201, template(), correlation);
  if (request.method === "POST" && url.pathname === `/credit/notificacoes/templates/${IDS.template}/aprovar`) return send(response, 200, template("aprovado"), correlation);
  if (request.method === "POST" && url.pathname === `/credit/notificacoes/templates/${IDS.template}/ativar`) return send(response, 200, template("ativo"), correlation);
  if (request.method === "POST" && url.pathname === `/credit/notificacoes/${IDS.notification}/conciliar`) return send(response, 200, notification("conciliada"), correlation);
  return send(response, 404, { codigo: "recurso_indisponivel", mensagem: "Recurso indisponivel." }, correlation);
});

server.listen(port, "127.0.0.1");
for (const signal of ["SIGINT", "SIGTERM"]) process.on(signal, () => server.close(() => process.exit(0)));
