import "server-only";

import { createBackendClient } from "../api/client.server";
import {
  INITIAL_WHATSAPP_ACTION_STATE,
  WHATSAPP_MANAGE_PERMISSION,
  WHATSAPP_READ_PERMISSION,
  hasExactPermission,
  isWhatsAppConnection,
  isWhatsAppQrCode,
  type WhatsAppActionState,
  type WhatsAppPermission,
  type WhatsAppReadResult,
} from "../whatsapp/whatsapp-policy";

import { ApiProblem, apiProblemFromResponse, correlationId, createCookieAuthenticatedFetch, type BffDependencies } from "./backend.server";
import type { OperationalContext } from "./context.server";
import type { CookieStore } from "./session.server";

type TypedClient = ReturnType<typeof createBackendClient>;

const ROTA_CONEXAO = "/platform/whatsapp/conexao" as const;

/**
 * BFF da conexao de WhatsApp (IMP-369).
 *
 * **Nao envia `Idempotency-Key`.** As tres escritas sao isentas pela
 * [ADR-019](../../../../docs/architecture/adrs/ADR-019-isencao-de-idempotency-key-nas-escritas-da-conexao-de-whatsapp.md),
 * e mandar o header assim mesmo faria o contrato divergir do snapshot governado —
 * que e verificado por teste.
 */

function correlationOf(response: Response, fallback: string): string {
  const header = response.headers.get("X-Correlation-ID");
  return header && header.length > 0 ? header : fallback;
}

async function problemOf(response: Response, fallback: string): Promise<ApiProblem> {
  try {
    return await apiProblemFromResponse(response, correlationOf(response, fallback));
  } catch {
    return new ApiProblem({ status: response.status, codigo: "resposta_backend_invalida", mensagem: "Servico temporariamente indisponivel.", correlationId: correlationOf(response, fallback) });
  }
}

function negado(correlation: string): ApiProblem {
  return new ApiProblem({ status: 403, codigo: "acesso_negado", mensagem: "Acao indisponivel para este acesso.", correlationId: correlation });
}

function indisponivel(correlation: string): ApiProblem {
  return new ApiProblem({ status: 502, codigo: "backend_indisponivel", mensagem: "Servico temporariamente indisponivel.", correlationId: correlation });
}

function problemState(problem: ApiProblem): WhatsAppActionState {
  return { kind: "problem", message: problem.message, status: problem.status, correlationId: problem.correlationId };
}

async function comCliente<T>(
  cookies: CookieStore,
  dependencies: BffDependencies,
  correlation: string,
  usar: (client: TypedClient) => Promise<T>,
): Promise<T> {
  const authenticatedFetch = await createCookieAuthenticatedFetch(cookies, dependencies, correlation);
  return usar(createBackendClient(dependencies.config.backendUrl, { fetch: authenticatedFetch }));
}

/** Estado da conexao, lido AO VIVO do provedor. E a fonte do polling da tela. */
export async function readWhatsAppConnection(
  cookies: CookieStore,
  context: OperationalContext,
  dependencies: BffDependencies,
): Promise<WhatsAppReadResult> {
  const correlation = correlationId();
  if (!hasExactPermission(context.permissoes, WHATSAPP_READ_PERMISSION)) {
    const problem = negado(correlation);
    return { kind: "problem", message: problem.message, status: problem.status, correlationId: problem.correlationId };
  }
  try {
    const result = await comCliente(cookies, dependencies, correlation, (client) => client.GET(ROTA_CONEXAO, {
      params: { header: { "X-Correlation-ID": correlation } },
    }));
    if (result.response.status !== 200) {
      const problem = await problemOf(result.response, correlation);
      return { kind: "problem", message: problem.message, status: problem.status, correlationId: problem.correlationId };
    }
    if (!isWhatsAppConnection(result.data)) {
      const problem = new ApiProblem({ status: 502, codigo: "resposta_backend_invalida", mensagem: "Servico temporariamente indisponivel.", correlationId: correlationOf(result.response, correlation) });
      return { kind: "problem", message: problem.message, status: problem.status, correlationId: problem.correlationId };
    }
    return { kind: "ready", connection: result.data };
  } catch (error) {
    const problem = error instanceof ApiProblem ? error : indisponivel(correlation);
    return { kind: "problem", message: problem.message, status: problem.status, correlationId: problem.correlationId };
  }
}

async function escrita(
  cookies: CookieStore,
  context: OperationalContext,
  dependencies: BffDependencies,
  permission: WhatsAppPermission,
  chamar: (client: TypedClient, correlation: string) => Promise<{ data?: unknown; response: Response }>,
  mensagem: string,
  extrairQr = false,
): Promise<WhatsAppActionState> {
  const correlation = correlationId();
  if (!hasExactPermission(context.permissoes, permission)) return problemState(negado(correlation));
  try {
    const result = await comCliente(cookies, dependencies, correlation, (client) => chamar(client, correlation));
    if (result.response.status !== 200) return problemState(await problemOf(result.response, correlation));
    const responseCorrelation = correlationOf(result.response, correlation);
    if (extrairQr) {
      if (!isWhatsAppQrCode(result.data)) {
        return problemState(new ApiProblem({ status: 502, codigo: "resposta_backend_invalida", mensagem: "Servico temporariamente indisponivel.", correlationId: responseCorrelation }));
      }
      // `qrcode_base64` nulo NAO e falha: o provedor responde "aguarde" logo apos
      // conectar, e a tela faz polling. Virar erro aqui faria o caminho feliz
      // parecer quebrado exatamente no momento mais comum.
      return { kind: "success", message: mensagem, correlationId: responseCorrelation, qrcode: result.data.qrcode_base64 ?? null };
    }
    if (!isWhatsAppConnection(result.data)) {
      return problemState(new ApiProblem({ status: 502, codigo: "resposta_backend_invalida", mensagem: "Servico temporariamente indisponivel.", correlationId: responseCorrelation }));
    }
    return { kind: "success", message: mensagem, correlationId: responseCorrelation };
  } catch (error) {
    return problemState(error instanceof ApiProblem ? error : indisponivel(correlation));
  }
}

/** Cria a instancia se preciso e devolve o QR de AGORA. Repetir e o uso normal. */
export async function connectWhatsApp(
  cookies: CookieStore,
  context: OperationalContext,
  dependencies: BffDependencies,
): Promise<WhatsAppActionState> {
  return escrita(cookies, context, dependencies, WHATSAPP_MANAGE_PERMISSION, (client, correlation) => client.POST(ROTA_CONEXAO, {
    params: { header: { "X-Correlation-ID": correlation } },
  }), "QR gerado. Escaneie no WhatsApp do aparelho.", true);
}

/** Encerra o pareamento. A instancia permanece no provedor. */
export async function disconnectWhatsApp(
  cookies: CookieStore,
  context: OperationalContext,
  dependencies: BffDependencies,
): Promise<WhatsAppActionState> {
  return escrita(cookies, context, dependencies, WHATSAPP_MANAGE_PERMISSION, (client, correlation) => client.DELETE(ROTA_CONEXAO, {
    params: { header: { "X-Correlation-ID": correlation } },
  }), "WhatsApp desconectado.");
}

export { INITIAL_WHATSAPP_ACTION_STATE };
