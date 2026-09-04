import { createServer } from "node:http";

const portArgument = process.argv.indexOf("--port");
const port = portArgument >= 0 ? Number(process.argv[portArgument + 1]) : 3201;

function send(response, status, body, correlation = "corr-fixture-289") {
  response.writeHead(status, {
    "Cache-Control": "no-store",
    "Content-Type": "application/json",
    "X-Correlation-ID": correlation,
  });
  response.end(body === undefined ? undefined : JSON.stringify(body));
}

async function jsonBody(request) {
  const chunks = [];
  for await (const chunk of request) chunks.push(chunk);
  return JSON.parse(Buffer.concat(chunks).toString("utf8"));
}

function loginMode(body) {
  const email = String(body.email ?? "");
  const match = email.match(/\+([^@]+)/);
  return String(match?.[1] ?? body.identificador_institucional ?? "ACME").toLowerCase();
}
const context = {
  carteira_padrao: { id: "wallet-e2e", nome: "Carteira Centro" },
  perfil: { id: "profile-e2e", nome: "Operador" },
  permissoes: ["devedor.ler"],
  tenant: { id: "tenant-e2e", identificador_institucional: "ACME", nome: "Instituicao ACME" },
  usuario: { email: "operador@example.test", id: "user-e2e", nome: "Operador E2E" },
    whatsapp: { numero: "556299999999", pareada: true },
};

let loopContextCalls = 0;

const server = createServer(async (request, response) => {
  const url = new URL(request.url ?? "/", `http://127.0.0.1:${port}`);
  const correlation = request.headers["x-correlation-id"] ?? "corr-fixture-289";
  if (request.method === "GET" && url.pathname === "/health") {
    send(response, 200, { checks: { database: "healthy" }, service: "api", status: "healthy" }, String(correlation));
    return;
  }
  if (request.method === "POST" && url.pathname === "/auth/login") {
    const body = await jsonBody(request);
    const mode = loginMode(body);
    if (mode === "loop") loopContextCalls = 0;
    const accessToken = mode === "expirado" ? "access-old"
      : mode === "loop" ? "access-loop-old"
        : mode === "falha" ? "access-error"
        : mode === "sem-carteira" ? "access-conflict" : "access-ok";
    send(response, 200, {
      access_token: accessToken,
      access_token_expira_em: "2099-08-13T12:15:00.000Z",
      refresh_token: `refresh-${mode}`,
      refresh_token_expira_em: "2099-08-20T12:00:00.000Z",
      tenant_id: "tenant-e2e",
      token_type: "bearer",
      usuario_id: "user-e2e",
    }, String(correlation));
    return;
  }
  if (request.method === "POST" && url.pathname === "/auth/refresh") {
    const body = await jsonBody(request);
    const loop = body.refresh_token === "refresh-loop";
    send(response, 200, {
      access_token: loop ? "access-loop-new" : "access-new",
      access_token_expira_em: "2099-08-13T12:30:00.000Z",
      tenant_id: "tenant-e2e",
      token_type: "bearer",
      usuario_id: "user-e2e",
    }, String(correlation));
    return;
  }
  if (request.method === "POST" && url.pathname === "/auth/logout") {
    response.writeHead(204, { "X-Correlation-ID": String(correlation) });
    response.end();
    return;
  }
  if (request.method === "GET" && url.pathname === "/iam/contexto-atual") {
    const authorization = request.headers.authorization;
    if (authorization === "Bearer access-old") {
      send(response, 401, { codigo: "autenticacao_recusada", mensagem: "Autenticacao recusada." }, String(correlation));
      return;
    }
    if (authorization === "Bearer access-conflict") {
      send(response, 409, { codigo: "contexto_operacional_incompleto", mensagem: "Contexto operacional corrente indisponivel." }, String(correlation));
      return;
    }
    if (authorization === "Bearer access-loop-old") {
      send(response, 401, { codigo: "autenticacao_recusada", mensagem: "Autenticacao recusada." }, String(correlation));
      return;
    }
    if (authorization === "Bearer access-loop-new") {
      loopContextCalls += 1;
      if (loopContextCalls === 1) {
        send(response, 200, context, String(correlation));
      } else {
        send(response, 401, { codigo: "autenticacao_recusada", mensagem: "Autenticacao recusada." }, String(correlation));
      }
      return;
    }
    if (authorization === "Bearer access-error") {
      send(response, 500, { codigo: "interno", mensagem: "stack secreta" }, String(correlation));
      return;
    }
    if (authorization === "Bearer access-ok" || authorization === "Bearer access-new") {
      send(response, 200, context, String(correlation));
      return;
    }
    send(response, 401, { codigo: "autenticacao_recusada", mensagem: "Autenticacao recusada." }, String(correlation));
    return;
  }
  send(response, 404, { codigo: "recurso_indisponivel", mensagem: "Recurso nao encontrado ou indisponivel." }, String(correlation));
});

server.listen(port, "127.0.0.1");

for (const signal of ["SIGINT", "SIGTERM"]) {
  process.on(signal, () => server.close(() => process.exit(0)));
}
