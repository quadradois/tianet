import { createServer } from "node:http";

const argument = process.argv.indexOf("--port");
const port = argument >= 0 ? Number(process.argv[argument + 1]) : 3208;
const id = (value) => `00000000-0000-4000-8000-${String(value).padStart(12, "0")}`;
const IDS = { commitment: id(80), communication: id(82), debtor: id(10), loan: id(40), notification: id(84), profile: id(4), reminder: id(81), tenant: id(1), user: id(2), wallet: id(3) };

function send(response, status, body, correlation = "corr-agenda-296") {
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
  if (mode === "leitura") return ["agenda.ler", "comunicacao.ler"];
  return ["agenda.ler", "agenda.compromisso.gerir", "agenda.lembrete.gerir", "notificacao.conciliar", "comunicacao.registrar", "comunicacao.ler"];
}

function operationalContext(mode) {
  const granted = permissions(mode);
  return {
    carteira_padrao: { id: IDS.wallet, nome: "Carteira Centro" },
    perfil: granted.length ? { id: IDS.profile, nome: "Operador Agenda" } : null,
    permissoes: granted,
    tenant: { id: IDS.tenant, identificador_institucional: "ACME", nome: "Instituicao ACME" },
    usuario: { email: "operador@example.test", id: IDS.user, nome: "Operador Agenda" },
  };
}

function commitment(overrides = {}) {
  return { agenda_item_id: IDS.commitment, atualizado_em: null, carteira_id: IDS.wallet, devedor_id: IDS.debtor, emprestimo_id: IDS.loan, estado: "aberto", previsto_para: "2026-08-14T15:00:00Z", tenant_id: IDS.tenant, titulo: "Retorno operacional", usuario_solicitante_id: IDS.user, ...overrides };
}

function reminder(overrides = {}) {
  return { agenda_item_id: IDS.commitment, carteira_id: IDS.wallet, enviado_por_usuario_id: IDS.user, estado: "programa", horario: "2026-08-14T14:30:00Z", lembrete_id: IDS.reminder, mensagem: "Ligar antes do retorno", tenant_id: IDS.tenant, ...overrides };
}

function communication(overrides = {}) {
  return { agenda_item_id: IDS.commitment, canal: "telefone", carteira_id: IDS.wallet, cobranca_acao_id: null, devedor_id: IDS.debtor, emprestimo_id: IDS.loan, ocorrido_em: "2026-08-14T16:00:00Z", parcela_id: null, registro_id: IDS.communication, responsavel_id: IDS.user, resultado: "Retorno agendado", resumo: "Contato realizado", tenant_id: IDS.tenant, ...overrides };
}

function notification() {
  return { carteira_id: IDS.wallet, codigo_resultado: "conciliado", estado: "enviado", id: IDS.notification, job_id: id(85), lembrete_id: IDS.reminder, provider_message_id: "provider-296", resultado_em: "2026-08-14T16:10:00Z" };
}

const server = createServer(async (request, response) => {
  const url = new URL(request.url ?? "/", `http://127.0.0.1:${port}`);
  const correlation = String(request.headers["x-correlation-id"] ?? "corr-agenda-296");
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
  if (mode === "nao-encontrado") return send(response, 404, { codigo: "agenda_nao_encontrada", mensagem: "detalhe cross-carteira" }, correlation);
  if (mode === "estados") return send(response, 500, { codigo: "interno", mensagem: "stack secreta" }, "corr-agenda-states-296");

  if (request.method === "GET" && url.pathname === "/credit/agenda") {
    if (mode === "vazio") return send(response, 200, { compromissos: [], lembretes: [], total: 0 }, correlation);
    return send(response, 200, { compromissos: [commitment(), commitment({ agenda_item_id: id(86), estado: "reagendado", titulo: "Retorno reagendado" })], lembretes: [reminder()], total: 3 }, correlation);
  }
  if (request.method === "GET" && url.pathname === "/credit/comunicacoes") {
    if (mode === "vazio") return send(response, 200, { registros: [], total: 0 }, correlation);
    return send(response, 200, { registros: [communication()], total: 1 }, correlation);
  }
  if (request.method === "POST" && url.pathname === `/credit/carteiras/${IDS.wallet}/devedores/${IDS.debtor}/agenda/compromissos`) return send(response, 200, commitment({ titulo: "Retorno criado" }), correlation);
  if (request.method === "POST" && url.pathname === `/credit/agenda/compromissos/${IDS.commitment}/lembretes`) return send(response, 200, reminder({ mensagem: "Lembrete criado" }), correlation);
  if (request.method === "POST" && url.pathname === `/credit/agenda/compromissos/${IDS.commitment}/reagendar`) return send(response, 200, commitment({ estado: "reagendado" }), correlation);
  if (request.method === "POST" && url.pathname === `/credit/agenda/compromissos/${IDS.commitment}/concluir`) return send(response, 200, commitment({ estado: "concluido" }), correlation);
  if (request.method === "POST" && url.pathname === `/credit/agenda/compromissos/${IDS.commitment}/cancelar`) return send(response, 200, commitment({ estado: "cancelado" }), correlation);
  if (request.method === "POST" && url.pathname === `/credit/agenda/lembretes/${IDS.reminder}/reagendar`) return send(response, 200, reminder({ horario: "2026-08-15T09:00:00Z" }), correlation);
  if (request.method === "POST" && url.pathname === `/credit/agenda/lembretes/${IDS.reminder}/enviar`) return send(response, 200, notification(), correlation);
  if (request.method === "POST" && url.pathname === `/credit/agenda/lembretes/${IDS.reminder}/concluir`) return send(response, 200, reminder({ estado: "concluido" }), correlation);
  if (request.method === "POST" && url.pathname === `/credit/agenda/lembretes/${IDS.reminder}/cancelar`) return send(response, 200, reminder({ estado: "cancelado" }), correlation);
  if (request.method === "POST" && url.pathname === `/credit/carteiras/${IDS.wallet}/devedores/${IDS.debtor}/comunicacoes`) return send(response, 200, communication({ resumo: "Comunicacao registrada" }), correlation);
  return send(response, 404, { codigo: "agenda_nao_encontrada", mensagem: "Recurso indisponivel." }, correlation);
});

server.listen(port, "127.0.0.1");
for (const signal of ["SIGINT", "SIGTERM"]) process.on(signal, () => server.close(() => process.exit(0)));
