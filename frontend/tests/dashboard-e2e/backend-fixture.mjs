import { createServer } from "node:http";

const argument = process.argv.indexOf("--port");
const port = argument >= 0 ? Number(process.argv[argument + 1]) : 3202;
const id = (value) => `00000000-0000-4000-8000-${String(value).padStart(12, "0")}`;
const IDS = { tenant: id(1), user: id(2), wallet: id(3), profile: id(4), loan1: id(5), loan2: id(6), debtor1: id(7), debtor2: id(8), agenda: id(9), debtor: id(10), reminder: id(11) };

function send(response, status, body, correlation = "corr-dashboard-290") {
  response.writeHead(status, { "Cache-Control": "no-store", "Content-Type": "application/json", "X-Correlation-ID": correlation });
  response.end(body === undefined ? undefined : JSON.stringify(body));
}

async function jsonBody(request) {
  const chunks = [];
  for await (const chunk of request) chunks.push(chunk);
  return JSON.parse(Buffer.concat(chunks).toString("utf8"));
}

function modeFromAuthorization(request) {
  return String(request.headers.authorization ?? "").replace(/^Bearer access-/, "");
}

function permissions(mode) {
  if (mode === "nenhuma") return [];
  if (mode === "parcial") return ["relatorios.operacionais.ler"];
  return ["relatorios.operacionais.ler", "agenda.ler", "cobranca.caso.ler"];
}

function operationalContext(mode) {
  const granted = permissions(mode);
  return {
    carteira_padrao: { id: IDS.wallet, nome: "Carteira Centro" },
    perfil: granted.length ? { id: IDS.profile, nome: "Operador" } : null,
    permissoes: granted,
    tenant: { id: IDS.tenant, identificador_institucional: "ACME", nome: "Instituicao ACME" },
    usuario: { email: "operador@example.test", id: IDS.user, nome: "Operador Dashboard" },
  };
}

function summary(referenceDate, empty = false) {
  return { carteira_id: IDS.wallet, data_referencia: referenceDate, operacoes_ativas: empty ? 0 : 7, operacoes_quitadas: empty ? 0 : 3, acertos_pendentes: 1, tenant_id: IDS.tenant, total_operacoes: empty ? 0 : 10, principal_a_receber: empty ? "0.00" : "12345.67", total_realizado: empty ? "0.00" : "4567.89" };
}

function dueDates(referenceDate, empty = false) {
  return { carteira_id: IDS.wallet, data_referencia: referenceDate, tenant_id: IDS.tenant, total: empty ? 0 : 2, itens: empty ? [] : [
    { acerto_em: "2026-08-10", devedor_id: IDS.debtor1, dia_de_acerto: 10, dias_sem_pagamento: 4, emprestimo_id: IDS.loan1, principal_original: "500.00", situacao: "pendente" },
    { acerto_em: "2026-08-20", devedor_id: IDS.debtor2, dia_de_acerto: 20, dias_sem_pagamento: 0, emprestimo_id: IDS.loan2, principal_original: "700.00", situacao: "em dia" },
  ] };
}

function agenda(empty = false) {
  return { total: empty ? 0 : 2, compromissos: empty ? [] : [{ agenda_item_id: IDS.agenda, atualizado_em: null, carteira_id: IDS.wallet, devedor_id: IDS.debtor, emprestimo_id: null, estado: "aberto", previsto_para: "2026-08-13T12:00:00-03:00", tenant_id: IDS.tenant, titulo: "Contato operacional com o cliente", usuario_solicitante_id: IDS.user }], lembretes: empty ? [] : [{ agenda_item_id: IDS.agenda, carteira_id: IDS.wallet, enviado_por_usuario_id: IDS.user, estado: "enviado", horario: "2026-08-13T12:05:00-03:00", lembrete_id: IDS.reminder, mensagem: "Lembrete oficial vinculado", tenant_id: IDS.tenant }] };
}

function collection(empty = false, many = false) {
  const count = empty ? 0 : many ? 18 : 2;
  return { total: count, items: Array.from({ length: count }, (_, index) => ({ carteira_id: IDS.wallet, caso_id: id(100 + index), criado_em: `2026-08-13T10:${String(index).padStart(2, "0")}:00Z`, devedor_id: id(200 + index), emprestimo_id: null, estado: "pendente", origem: "manual", tenant_id: IDS.tenant, titulo: `Caso operacional ${index + 1} com descricao extensa para validar overflow contido`, total_pendente: `${index + 1}00.00` })) };
}

const server = createServer(async (request, response) => {
  const url = new URL(request.url ?? "/", `http://127.0.0.1:${port}`);
  const correlation = String(request.headers["x-correlation-id"] ?? "corr-dashboard-290");
  if (request.method === "GET" && url.pathname === "/health") return send(response, 200, { checks: { database: "healthy" }, service: "api", status: "healthy" }, correlation);
  if (request.method === "POST" && url.pathname === "/auth/login") {
    const body = await jsonBody(request);
    const selected = String(body.identificador_institucional).toLowerCase();
    const mode = selected === "expirado" ? "old" : selected === "acme" ? "acme" : selected;
    return send(response, 200, { access_token: `access-${mode}`, access_token_expira_em: "2099-08-13T12:15:00Z", refresh_token: `refresh-${mode}`, refresh_token_expira_em: "2099-08-20T12:00:00Z", tenant_id: IDS.tenant, token_type: "bearer", usuario_id: IDS.user }, correlation);
  }
  if (request.method === "POST" && url.pathname === "/auth/refresh") return send(response, 200, { access_token: "access-acme", access_token_expira_em: "2099-08-13T12:30:00Z", tenant_id: IDS.tenant, token_type: "bearer", usuario_id: IDS.user }, correlation);
  if (request.method === "POST" && url.pathname === "/auth/logout") { response.writeHead(204, { "X-Correlation-ID": correlation }); response.end(); return; }
  if (request.method === "GET" && url.pathname === "/iam/contexto-atual") {
    const mode = modeFromAuthorization(request);
    if (mode === "old") return send(response, 401, { codigo: "autenticacao_recusada", mensagem: "Autenticacao recusada." }, correlation);
    return send(response, 200, operationalContext(mode), correlation);
  }
  const mode = modeFromAuthorization(request);
  if (mode === "secao-expirada" && url.pathname.endsWith("/relatorios/resumo")) return send(response, 401, { codigo: "autenticacao_recusada", mensagem: "Autenticacao recusada." }, correlation);
  if (mode === "nao-encontrado" && url.pathname.endsWith("/resumo")) return send(response, 404, { codigo: "recurso_indisponivel", mensagem: "detalhe cross tenant" }, correlation);
  if (mode === "estados" && url.pathname.endsWith("/resumo")) return send(response, 500, { codigo: "interno", mensagem: "stack secreta" }, "corr-dashboard-states-290");
  if (mode === "estados" && url.pathname === "/credit/agenda") return send(response, 403, { codigo: "acesso_negado", mensagem: "regra interna" }, correlation);
  if (mode === "lento") await new Promise((resolve) => setTimeout(resolve, 350));
  const empty = mode === "vazio" || mode === "estados";
  if (request.method === "GET" && url.pathname.endsWith("/relatorios/resumo")) {
    const referenceDate = url.searchParams.get("data_referencia");
    if (!url.pathname.includes(`/carteiras/${IDS.wallet}/`) || !/^\d{4}-\d{2}-\d{2}$/.test(referenceDate ?? "")) return send(response, 400, { codigo: "periodo_invalido", mensagem: "Query invalida." }, correlation);
    return send(response, 200, summary(referenceDate, empty), correlation);
  }
  if (request.method === "GET" && url.pathname.endsWith("/relatorios/vencimentos")) {
    const referenceDate = url.searchParams.get("data_referencia");
    if (!url.pathname.includes(`/carteiras/${IDS.wallet}/`) || !/^\d{4}-\d{2}-\d{2}$/.test(referenceDate ?? "")) return send(response, 400, { codigo: "periodo_invalido", mensagem: "Query invalida." }, correlation);
    return send(response, 200, dueDates(referenceDate, empty), correlation);
  }
  if (request.method === "GET" && url.pathname === "/credit/agenda") {
    const validWindow = url.searchParams.get("janela_inicio") && url.searchParams.get("janela_fim");
    if (url.searchParams.get("carteira_id") !== IDS.wallet || url.searchParams.get("incluir_lembretes") !== "true" || !validWindow) return send(response, 400, { codigo: "periodo_invalido", mensagem: "Query invalida." }, correlation);
    return send(response, 200, agenda(mode === "vazio"), correlation);
  }
  if (request.method === "GET" && url.pathname === "/credit/cobrancas/casos") {
    if (url.searchParams.get("carteira_id") !== IDS.wallet) return send(response, 400, { codigo: "periodo_invalido", mensagem: "Query invalida." }, correlation);
    return send(response, 200, collection(mode === "vazio", mode === "estados"), correlation);
  }
  return send(response, 404, { codigo: "recurso_indisponivel", mensagem: "Recurso indisponivel." }, correlation);
});

server.listen(port, "127.0.0.1");
for (const signal of ["SIGINT", "SIGTERM"]) process.on(signal, () => server.close(() => process.exit(0)));
