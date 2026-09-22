import { createServer } from "node:http";

const portIndex = process.argv.indexOf("--port");
const port = portIndex >= 0 ? Number(process.argv[portIndex + 1]) : 3211;

/**
 * Backend falso da jornada de Recebimento (IMP-388).
 *
 * O estado e por "modo" (sufixo do e-mail de login), para cada teste comecar
 * de onde precisa sem depender da ordem: `novo` (nada configurado) e
 * `leitura` (sem a permissao de configurar).
 */
const estados = new Map();

function send(response, status, body, correlation = "corr-pagamentos-e2e") {
  response.writeHead(status, { "Cache-Control": "no-store", "Content-Type": "application/json", "X-Correlation-ID": correlation });
  response.end(JSON.stringify(body));
}

async function body(request) {
  const chunks = [];
  for await (const chunk of request) chunks.push(chunk);
  return JSON.parse(Buffer.concat(chunks).toString("utf8"));
}

function mode(request) {
  return String(request.headers.authorization ?? "").match(/access-([a-z]+)/)?.[1] ?? "novo";
}

function context(selected) {
  return {
    carteira_padrao: { id: "wallet-e2e", nome: "Carteira" },
    perfil: { id: "profile-e2e", nome: "Administrador" },
    permissoes: selected === "leitura" ? ["relatorios.operacionais.ler"] : ["mercadopago.configurar"],
    tenant: { id: "tenant-e2e", identificador_institucional: "ACME", nome: "ACME" },
    usuario: { email: "operador@example.test", id: "user-e2e", nome: "Operador" },
    whatsapp: { alerta_queda_ativa: false, numero: null, pareada: false, queda_detectada_em: null },
  };
}

function atual(selected) {
  if (!estados.has(selected)) {
    estados.set(selected, { habilitado: false, credencial_configurada: false, assinatura_configurada: false, testado_em: null });
  }
  const estado = estados.get(selected);
  return { tenant_id: "tenant-e2e", atualizado_em: "2026-09-22T12:00:00Z", atualizado_por: "user-e2e", ...estado };
}

const server = createServer(async (request, response) => {
  const url = new URL(request.url ?? "//", `http://127.0.0.1:${port}`);
  const correlation = String(request.headers["x-correlation-id"] ?? "corr-pagamentos-e2e");
  if (request.method === "GET" && url.pathname === "/health") return send(response, 200, { status: "healthy" }, correlation);
  if (request.method === "POST" && url.pathname === "/auth/login") {
    const login = await body(request);
    const selected = String(login.email).match(/\+([^@]+)/)?.[1] ?? "novo";
    estados.delete(selected);
    return send(response, 200, { access_token: `access-${selected}`, access_token_expira_em: "2099-01-01T00:00:00Z", refresh_token: `refresh-${selected}`, refresh_token_expira_em: "2099-01-02T00:00:00Z", tenant_id: "tenant-e2e", token_type: "bearer", usuario_id: "user-e2e" }, correlation);
  }
  if (request.method === "GET" && url.pathname === "/iam/contexto-atual") return send(response, 200, context(mode(request)), correlation);

  const selected = mode(request);
  if (url.pathname === "/platform/mercadopago/configuracao") {
    if (request.method === "GET") return send(response, 200, atual(selected), correlation);
    if (request.method === "PUT") {
      if (!request.headers["idempotency-key"]) return send(response, 400, { codigo: "idempotencia_invalida", mensagem: "Chave ausente." }, correlation);
      await body(request);
      estados.set(selected, { ...atual(selected), credencial_configurada: true, assinatura_configurada: true, testado_em: null });
      return send(response, 200, atual(selected), correlation);
    }
  }
  if (request.method === "POST" && url.pathname === "/platform/mercadopago/configuracao/testar") {
    estados.set(selected, { ...atual(selected), testado_em: "2026-09-22T12:00:00Z" });
    return send(response, 200, atual(selected), correlation);
  }
  if (request.method === "POST" && url.pathname === "/platform/mercadopago/configuracao/habilitar") {
    const estado = atual(selected);
    if (estado.testado_em === null) return send(response, 422, { codigo: "regra_violada", mensagem: "Teste a credencial antes de ligar." }, correlation);
    estados.set(selected, { ...estado, habilitado: true });
    return send(response, 200, atual(selected), correlation);
  }
  if (request.method === "POST" && url.pathname === "/platform/mercadopago/configuracao/desabilitar") {
    estados.set(selected, { ...atual(selected), habilitado: false });
    return send(response, 200, atual(selected), correlation);
  }
  if (url.pathname === "/platform/mercadopago/chave-pix") {
    const estado = atual(selected);
    if (request.method === "GET") {
      return send(response, 200, estado.chavePix ?? { tipo: null, valor: null, favorecido: null, configurada: false }, correlation);
    }
    if (request.method === "PUT") {
      if (!request.headers["idempotency-key"]) return send(response, 400, { codigo: "idempotencia_invalida", mensagem: "Chave ausente." }, correlation);
      const payload = await body(request);
      const chavePix = { tipo: payload.tipo, valor: payload.valor, favorecido: payload.favorecido, configurada: true };
      estados.set(selected, { ...estado, chavePix });
      return send(response, 200, chavePix, correlation);
    }
  }
  return send(response, 404, { codigo: "recurso_nao_encontrado", mensagem: "Recurso não encontrado." }, correlation);
});

server.listen(port, "127.0.0.1");
