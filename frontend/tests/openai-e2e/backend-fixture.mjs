import { createServer } from "node:http";

const portIndex = process.argv.indexOf("--port");
const port = portIndex >= 0 ? Number(process.argv[portIndex + 1]) : 3210;
const states = new Map();
const pendingReads = new Map();

function send(response, status, body, correlation = "corr-openai-e2e") {
  response.writeHead(status, { "Cache-Control": "no-store", "Content-Type": "application/json", "X-Correlation-ID": correlation });
  response.end(JSON.stringify(body));
}

async function body(request) {
  const chunks = [];
  for await (const chunk of request) chunks.push(chunk);
  return JSON.parse(Buffer.concat(chunks).toString("utf8"));
}

function mode(request) {
  return String(request.headers.authorization ?? "").match(/access-([a-z]+)/)?.[1] ?? "desconectado";
}

function context(selected) {
  return {
    carteira_padrao: { id: "wallet-e2e", nome: "Carteira" }, perfil: { id: "profile-e2e", nome: "Administrador" },
    permissoes: selected === "leitura" ? ["openai.conexao.ler"] : ["openai.conexao.ler", "openai.conexao.gerir"],
    tenant: { id: "tenant-e2e", identificador_institucional: "ACME", nome: "ACME" },
    usuario: { email: "operador@example.test", id: "user-e2e", nome: "Operador" },
    whatsapp: { alerta_queda_ativa: false, numero: null, pareada: false, queda_detectada_em: null },
  };
}

function connection(selected) {
  const state = states.get(selected) ?? (selected === "conectado" ? "CONECTADO" : "DESCONECTADO");
  const usageSummary = state === "CONECTADO" ? { observedAt: "2026-09-09T12:00:00Z", rateLimitsStatus: "ok", rateLimits: [{ limitId: "codex", planType: "plus", primary: { usedPercent: 25, windowDurationMinutes: 300, resetsAt: 1790000000 }, secondary: null }] } : null;
  return { enabled: true, processAvailable: true, accountConnected: state === "CONECTADO", planType: state === "CONECTADO" ? "plus" : null, state, usageSummary };
}

const server = createServer(async (request, response) => {
  const url = new URL(request.url ?? "//", `http://127.0.0.1:${port}`);
  const correlation = String(request.headers["x-correlation-id"] ?? "corr-openai-e2e");
  if (request.method === "GET" && url.pathname === "/health") return send(response, 200, { status: "healthy" }, correlation);
  if (request.method === "POST" && url.pathname === "/auth/login") {
    const login = await body(request); const selected = String(login.email).match(/\+([^@]+)/)?.[1] ?? "desconectado";
    states.set(selected, selected === "conectado" ? "CONECTADO" : "DESCONECTADO");
    return send(response, 200, { access_token: `access-${selected}`, access_token_expira_em: "2099-01-01T00:00:00Z", refresh_token: `refresh-${selected}`, refresh_token_expira_em: "2099-01-02T00:00:00Z", tenant_id: "tenant-e2e", token_type: "bearer", usuario_id: "user-e2e" }, correlation);
  }
  if (request.method === "GET" && url.pathname === "/iam/contexto-atual") return send(response, 200, context(mode(request)), correlation);
  if (url.pathname === "/platform/openai/conexao") {
    const selected = mode(request);
    if (request.method === "GET") {
      const remaining = pendingReads.get(selected);
      if (remaining !== undefined) {
        if (remaining <= 1) { states.set(selected, "CONECTADO"); pendingReads.delete(selected); }
        else pendingReads.set(selected, remaining - 1);
      }
      return send(response, 200, connection(selected), correlation);
    }
    if (request.method === "DELETE") {
      if (!request.headers["idempotency-key"]) return send(response, 400, { codigo: "idempotencia_invalida", mensagem: "Chave ausente." }, correlation);
      states.set(selected, "DESCONECTADO"); pendingReads.delete(selected);
      return send(response, 200, { state: "DESCONECTADO", localLogout: true, remoteRevocationVerified: false }, correlation);
    }
  }
  if (request.method === "POST" && url.pathname === "/platform/openai/conexao/login") {
    const selected = mode(request); states.set(selected, "AGUARDANDO_USUARIO"); pendingReads.set(selected, 2);
    return send(response, 200, { verificationUrl: "https://auth.openai.com/codex/device", userCode: "ABCD-EFGH", expiresAt: "2099-01-01T00:10:00Z" }, correlation);
  }
  if (request.method === "GET" && url.pathname === "/platform/openai/diagnostico") return send(response, 200, { state: "CONECTADO", observedAt: "2026-09-09T12:00:00Z", accountStatus: "ok", accountConnected: true, planType: "plus", modelsStatus: "ok", models: [{ id: "gpt-test", displayName: "GPT Test", default: true }], rateLimitsStatus: "ok", rateLimits: [{ limitId: "codex", planType: "plus", primary: { usedPercent: 25, windowDurationMinutes: 300, resetsAt: 1790000000 }, secondary: null }] }, correlation);
  return send(response, 404, { codigo: "recurso_nao_encontrado", mensagem: "Recurso não encontrado." }, correlation);
});

server.listen(port, "127.0.0.1");
