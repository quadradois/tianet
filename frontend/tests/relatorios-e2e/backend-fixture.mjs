import { createServer } from "node:http";

const argument = process.argv.indexOf("--port");
const port = argument >= 0 ? Number(process.argv[argument + 1]) : 3209;
const id = (value) => `00000000-0000-4000-8000-${String(value).padStart(12, "0")}`;
const IDS = { loan: id(10), payment: id(12), profile: id(4), tenant: id(1), user: id(2), wallet: id(3) };

function send(response, status, body, correlation = "corr-relatorios-297") {
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
  return ["relatorios.operacionais.ler"];
}

function context(mode) {
  const granted = permissions(mode);
  return {
    carteira_padrao: { id: IDS.wallet, nome: "Carteira Centro" },
    perfil: granted.length ? { id: IDS.profile, nome: "Operador Relatorios" } : null,
    permissoes: granted,
    tenant: { id: IDS.tenant, identificador_institucional: "ACME", nome: "Instituicao ACME" },
    usuario: { email: "operador@example.test", id: IDS.user, nome: "Operador Relatorios" },
    whatsapp: { numero: "556299999999", pareada: true },
  };
}

function summary(referenceDate, empty = false) {
  return { carteira_id: IDS.wallet, data_referencia: referenceDate, operacoes_ativas: empty ? 0 : 6, operacoes_quitadas: empty ? 0 : 4, acertos_pendentes: 1, tenant_id: IDS.tenant, total_operacoes: empty ? 0 : 10, principal_a_receber: empty ? "0.00" : "98765.43", total_realizado: empty ? "0.00" : "54321.09" };
}

function dueDates(referenceDate, empty = false) {
  return { carteira_id: IDS.wallet, data_referencia: referenceDate, itens: empty ? [] : Array.from({ length: 14 }, (_, index) => ({ acerto_em: `2026-08-${String(10 + index).padStart(2, "0")}`, devedor_id: id(200 + index), dia_de_acerto: 10 + index, dias_sem_pagamento: index % 2 ? 0 : index + 1, emprestimo_id: id(100 + index), principal_original: `${index + 1}00.00`, situacao: index % 2 ? "em dia" : "pendente" })), tenant_id: IDS.tenant, total: empty ? 0 : 14 };
}

function payments(empty = false) {
  return { carteira_id: IDS.wallet, fim: "2026-08-31", inicio: "2026-08-01", operacoes_quitadas: empty ? [] : [IDS.loan], pagamentos: empty ? [] : [{ emprestimo_id: IDS.loan, estado: "confirmado", pagamento_id: IDS.payment, recebido_em: "2026-08-12", valor_recebido: "54321.09" }], tenant_id: IDS.tenant, total_realizado: empty ? "0.00" : "54321.09" };
}

function cashFlow(empty = false) {
  return { carteira_id: IDS.wallet, fim: "2026-08-31", inicio: "2026-08-01", itens: empty ? [] : Array.from({ length: 12 }, (_, index) => ({ acertos: index % 3, data: `2026-08-${String(index + 1).padStart(2, "0")}`, pagamento_ids: index % 2 ? [IDS.payment] : [], realizado: `${index + 1}00.00` })), tenant_id: IDS.tenant };
}

const server = createServer(async (request, response) => {
  const url = new URL(request.url ?? "/", `http://127.0.0.1:${port}`);
  const correlation = String(request.headers["x-correlation-id"] ?? "corr-relatorios-297");
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
  if (!url.pathname.includes(`/carteiras/${IDS.wallet}/`)) return send(response, 404, { codigo: "recurso_indisponivel", mensagem: "detalhe cross tenant" }, correlation);
  if (mode === "estados" && url.pathname.endsWith("/resumo")) return send(response, 500, { codigo: "interno", mensagem: "stack secreta" }, "corr-relatorios-states-297");
  if (mode === "nao-encontrado" && url.pathname.endsWith("/resumo")) return send(response, 404, { codigo: "recurso_indisponivel", mensagem: "detalhe cross tenant" }, correlation);
  const empty = mode === "vazio" || mode === "estados";
  if (request.method === "GET" && url.pathname.endsWith("/relatorios/resumo")) return send(response, 200, summary(url.searchParams.get("data_referencia"), empty), correlation);
  if (request.method === "GET" && url.pathname.endsWith("/relatorios/vencimentos")) return send(response, 200, dueDates(url.searchParams.get("data_referencia"), empty), correlation);
  if (request.method === "GET" && url.pathname.endsWith("/relatorios/pagamentos")) return send(response, 200, payments(empty), correlation);
  if (request.method === "GET" && url.pathname.endsWith("/relatorios/fluxo")) return send(response, 200, cashFlow(empty), correlation);
  return send(response, 404, { codigo: "recurso_indisponivel", mensagem: "Recurso indisponivel." }, correlation);
});

server.listen(port, "127.0.0.1");
for (const signal of ["SIGINT", "SIGTERM"]) process.on(signal, () => server.close(() => process.exit(0)));
