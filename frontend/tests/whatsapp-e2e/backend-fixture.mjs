import { createServer } from "node:http";

const portArgument = process.argv.indexOf("--port");
const port = portArgument >= 0 ? Number(process.argv[portArgument + 1]) : 3502;

// PNG 1x1 transparente. O conteudo nao importa: o que a jornada verifica e que a
// tela EXIBE o QR vindo do POST, e nunca do GET.
const QRCODE = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==";

function send(response, status, body, correlation = "corr-fixture-369") {
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
  return String(match?.[1] ?? "ausente").toLowerCase();
}

const PERMISSOES = {
  ausente: ["whatsapp.conexao.ler", "whatsapp.conexao.gerir"],
  pendente: ["whatsapp.conexao.ler", "whatsapp.conexao.gerir"],
  pareada: ["whatsapp.conexao.ler", "whatsapp.conexao.gerir"],
  // `fluxo` percorre o ciclo inteiro: conectar -> QR -> pareia sozinho na
  // proxima consulta -> desconectar. Existe para o teste que guarda o QR velho
  // nao reaparecendo depois do logout.
  fluxo: ["whatsapp.conexao.ler", "whatsapp.conexao.gerir"],
  soleitura: ["whatsapp.conexao.ler"],
};

// Consultas de estado por modo. O teste do polling usa isto para provar que o
// laco PARA — contar chamada e a unica forma de verificar ausencia de trafego.
const consultas = new Map();

// Modos que pareiam sozinhos depois de N consultas apos o `connect`, simulando o
// operador escaneando o QR.
//
// N=2 e nao 1 de proposito: a revalidacao que o Next dispara logo depois do
// `POST` ja consome uma consulta. Parear na primeira faria a tela pular direto
// para "Conectado" sem NUNCA mostrar o QR — e o teste que guarda o QR velho
// precisa ver o QR aparecer antes de desconectar.
const pareiaEm = new Map();

// Estado do pareamento por modo. `ausente` vira `pendente` depois do primeiro
// POST — e a transicao que a jornada percorre.
const conexoes = {
  ausente: { existe: false, pareada: false, conectado: false, instancia_nome: null, nome_exibicao: null, numero: null },
  pendente: { existe: true, pareada: false, conectado: true, instancia_nome: "tianet_tenant-e2e", nome_exibicao: null, numero: null },
  pareada: { existe: true, pareada: true, conectado: true, instancia_nome: "tianet_tenant-e2e", nome_exibicao: "Barbosa", numero: "556299999999" },
  soleitura: { existe: false, pareada: false, conectado: false, instancia_nome: null, nome_exibicao: null, numero: null },
  fluxo: { existe: false, pareada: false, conectado: false, instancia_nome: null, nome_exibicao: null, numero: null },
};

const estadoAtual = new Map();

function contexto(modo) {
  const conexao = estadoAtual.get(modo) ?? conexoes[modo] ?? conexoes.ausente;
  return {
    carteira_padrao: { id: "wallet-e2e", nome: "Carteira Centro" },
    perfil: { id: "profile-e2e", nome: "Operador" },
    permissoes: PERMISSOES[modo] ?? PERMISSOES.ausente,
    tenant: { id: "tenant-e2e", identificador_institucional: "ACME", nome: "Instituicao ACME" },
    usuario: { email: "operador@example.test", id: "user-e2e", nome: "Operador E2E" },
    whatsapp: { numero: conexao.numero, pareada: conexao.pareada },
  };
}

function modoDoToken(request) {
  const header = String(request.headers.authorization ?? "");
  const match = header.match(/access-([a-z]+)/);
  return match?.[1] ?? "ausente";
}

const server = createServer(async (request, response) => {
  const url = new URL(request.url ?? "/", `http://127.0.0.1:${port}`);
  const correlation = String(request.headers["x-correlation-id"] ?? "corr-fixture-369");

  // Rota so do teste: quantas consultas de estado este modo ja recebeu.
  if (request.method === "GET" && url.pathname === "/_fixture/consultas") {
    send(response, 200, { total: consultas.get(url.searchParams.get("modo") ?? "") ?? 0 }, correlation);
    return;
  }

  if (request.method === "GET" && url.pathname === "/health") {
    send(response, 200, { checks: { database: "healthy" }, service: "api", status: "healthy" }, correlation);
    return;
  }

  if (request.method === "POST" && url.pathname === "/auth/login") {
    const modo = loginMode(await jsonBody(request));
    estadoAtual.set(modo, { ...(conexoes[modo] ?? conexoes.ausente) });
    send(response, 200, {
      access_token: `access-${modo}`,
      access_token_expira_em: "2099-08-13T12:15:00.000Z",
      refresh_token: `refresh-${modo}`,
      refresh_token_expira_em: "2099-08-20T12:00:00.000Z",
      tenant_id: "tenant-e2e",
      token_type: "bearer",
      usuario_id: "user-e2e",
    }, correlation);
    return;
  }

  if (request.method === "GET" && url.pathname === "/iam/contexto-atual") {
    send(response, 200, contexto(modoDoToken(request)), correlation);
    return;
  }

  if (url.pathname === "/platform/whatsapp/conexao") {
    const modo = modoDoToken(request);
    if (request.method === "GET") {
      consultas.set(modo, (consultas.get(modo) ?? 0) + 1);
      const restantes = pareiaEm.get(modo);
      if (restantes !== undefined) {
        if (restantes <= 1) {
          pareiaEm.delete(modo);
          estadoAtual.set(modo, { ...conexoes.pareada });
        } else {
          pareiaEm.set(modo, restantes - 1);
        }
      }
      send(response, 200, estadoAtual.get(modo) ?? conexoes[modo] ?? conexoes.ausente, correlation);
      return;
    }
    if (request.method === "POST") {
      if (!PERMISSOES[modo]?.includes("whatsapp.conexao.gerir")) {
        send(response, 403, { codigo: "acesso_negado", mensagem: "Acao indisponivel para este acesso." }, correlation);
        return;
      }
      // Criar e conectar num gesto so: a instancia passa a existir e o QR sai.
      estadoAtual.set(modo, { ...conexoes.pendente });
      if (modo === "fluxo") pareiaEm.set(modo, 2);
      send(response, 200, { qrcode_base64: QRCODE }, correlation);
      return;
    }
    if (request.method === "DELETE") {
      estadoAtual.set(modo, { ...conexoes.pendente, pareada: false, conectado: false });
      send(response, 200, estadoAtual.get(modo), correlation);
      return;
    }
  }

  send(response, 404, { codigo: "recurso_nao_encontrado", mensagem: "Recurso nao encontrado" }, correlation);
});

server.listen(port, "127.0.0.1");
