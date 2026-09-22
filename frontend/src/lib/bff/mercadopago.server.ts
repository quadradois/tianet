import "server-only";

import { createBackendClient } from "../api/client.server";
import {
  INITIAL_MERCADOPAGO_ACTION_STATE,
  MERCADOPAGO_PERMISSION,
  hasMercadoPagoPermission,
  isMercadoPagoConfig,
  type MercadoPagoActionState,
  type MercadoPagoReadResult,
} from "../pagamentos/mercadopago-policy";

import { ApiProblem, apiProblemFromResponse, correlationId, createCookieAuthenticatedFetch, idempotencyKey, type BffDependencies } from "./backend.server";
import type { OperationalContext } from "./context.server";
import type { CookieStore } from "./session.server";

type TypedClient = ReturnType<typeof createBackendClient>;

const ROTA = "/platform/mercadopago/configuracao" as const;
const ROTA_TESTAR = "/platform/mercadopago/configuracao/testar" as const;
const ROTA_HABILITAR = "/platform/mercadopago/configuracao/habilitar" as const;
const ROTA_DESABILITAR = "/platform/mercadopago/configuracao/desabilitar" as const;

/**
 * BFF do interruptor do Mercado Pago (IMP-388).
 *
 * **O segredo entra e nao volta.** O backend nunca devolve `access_token` nem
 * `webhook_secret`; este modulo nao os guarda, nao os loga e nao os coloca em
 * nenhum estado que chegue ao cliente.
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

function problemState(problem: ApiProblem): Readonly<{ kind: "problem"; message: string; status: number; correlationId: string }> {
  return { kind: "problem", message: problem.message, status: problem.status, correlationId: problem.correlationId };
}

async function comCliente<T>(
  cookies: CookieStore,
  dependencies: BffDependencies,
  correlation: string,
  chamada: (client: TypedClient) => Promise<T>,
): Promise<T> {
  const fetchAutenticado = await createCookieAuthenticatedFetch(cookies, dependencies, correlation);
  return chamada(createBackendClient(dependencies.config.backendUrl, { fetch: fetchAutenticado }));
}

export async function readMercadoPagoConfig(
  cookies: CookieStore,
  context: OperationalContext,
  dependencies: BffDependencies,
): Promise<MercadoPagoReadResult> {
  const correlation = correlationId();
  if (!hasMercadoPagoPermission(context.permissoes)) return problemState(negado(correlation));
  try {
    const result = await comCliente(cookies, dependencies, correlation, (client) => client.GET(ROTA, {
      params: { header: { "X-Correlation-ID": correlation } },
    }));
    if (result.response.status !== 200) return problemState(await problemOf(result.response, correlation));
    if (!isMercadoPagoConfig(result.data)) {
      return problemState(new ApiProblem({ status: 502, codigo: "resposta_backend_invalida", mensagem: "Servico temporariamente indisponivel.", correlationId: correlationOf(result.response, correlation) }));
    }
    return { kind: "ready", config: result.data };
  } catch (error) {
    return problemState(error instanceof ApiProblem ? error : indisponivel(correlation));
  }
}

/** Le `credencial`/`assinatura` do formulario e envia com os nomes do contrato. */
export async function saveMercadoPagoCredentials(
  cookies: CookieStore,
  context: OperationalContext,
  dependencies: BffDependencies,
  formData: FormData,
): Promise<MercadoPagoActionState> {
  const correlation = correlationId();
  if (!hasMercadoPagoPermission(context.permissoes)) return problemState(negado(correlation));
  const accessToken = formData.get("credencial");
  const webhookSecret = formData.get("assinatura");
  if (typeof accessToken !== "string" || accessToken.trim().length < 10 || typeof webhookSecret !== "string" || webhookSecret.trim().length < 8) {
    return problemState(new ApiProblem({ status: 400, codigo: "payload_invalido", mensagem: "Informe o access token (10+ caracteres) e o segredo do webhook (8+).", correlationId: correlation }));
  }
  const chave = chaveDe(formData, correlation);
  if (typeof chave !== "string") return chave;
  try {
    const result = await comCliente(cookies, dependencies, correlation, (client) => client.PUT(ROTA, {
      params: { header: { "X-Correlation-ID": correlation, "Idempotency-Key": chave } },
      body: { access_token: accessToken.trim(), webhook_secret: webhookSecret.trim() },
    }));
    return await estadoDe(result, correlation, "credenciais", "Credenciais salvas. Teste antes de ligar o recebimento.");
  } catch (error) {
    return problemState(error instanceof ApiProblem ? error : indisponivel(correlation));
  }
}

export async function testMercadoPagoCredentials(
  cookies: CookieStore,
  context: OperationalContext,
  dependencies: BffDependencies,
  formData: FormData,
): Promise<MercadoPagoActionState> {
  return await acaoSimples(cookies, context, dependencies, formData, ROTA_TESTAR, "testar", "Credencial aceita pelo provedor.");
}

export async function enableMercadoPago(
  cookies: CookieStore,
  context: OperationalContext,
  dependencies: BffDependencies,
  formData: FormData,
): Promise<MercadoPagoActionState> {
  return await acaoSimples(cookies, context, dependencies, formData, ROTA_HABILITAR, "habilitar", "Recebimento por Pix ligado.");
}

export async function disableMercadoPago(
  cookies: CookieStore,
  context: OperationalContext,
  dependencies: BffDependencies,
  formData: FormData,
): Promise<MercadoPagoActionState> {
  return await acaoSimples(cookies, context, dependencies, formData, ROTA_DESABILITAR, "desabilitar", "Recebimento por Pix desligado. Cobrancas em aberto seguem valendo.");
}

function chaveDe(formData: FormData, correlation: string): string | Readonly<{ kind: "problem"; message: string; status: number; correlationId: string }> {
  const bruta = formData.get("idempotency_key");
  try {
    return idempotencyKey(true, typeof bruta === "string" ? bruta : undefined) ?? "";
  } catch (error) {
    return problemState(error instanceof ApiProblem ? error : indisponivel(correlation));
  }
}

async function estadoDe(
  result: { response: Response; data?: unknown },
  correlation: string,
  operacao: "credenciais" | "testar" | "habilitar" | "desabilitar",
  mensagem: string,
): Promise<MercadoPagoActionState> {
  if (result.response.status !== 200) return problemState(await problemOf(result.response, correlation));
  if (!isMercadoPagoConfig(result.data)) {
    return problemState(new ApiProblem({ status: 502, codigo: "resposta_backend_invalida", mensagem: "Servico temporariamente indisponivel.", correlationId: correlationOf(result.response, correlation) }));
  }
  return { kind: "success", message: mensagem, operacao, config: result.data, correlationId: correlationOf(result.response, correlation) };
}

async function acaoSimples(
  cookies: CookieStore,
  context: OperationalContext,
  dependencies: BffDependencies,
  formData: FormData,
  rota: typeof ROTA_TESTAR | typeof ROTA_HABILITAR | typeof ROTA_DESABILITAR,
  operacao: "testar" | "habilitar" | "desabilitar",
  mensagem: string,
): Promise<MercadoPagoActionState> {
  const correlation = correlationId();
  if (!hasMercadoPagoPermission(context.permissoes)) return problemState(negado(correlation));
  const chave = chaveDe(formData, correlation);
  if (typeof chave !== "string") return chave;
  try {
    const result = await comCliente(cookies, dependencies, correlation, (client) => client.POST(rota, {
      params: { header: { "X-Correlation-ID": correlation, "Idempotency-Key": chave } },
    }));
    return await estadoDe(result, correlation, operacao, mensagem);
  } catch (error) {
    return problemState(error instanceof ApiProblem ? error : indisponivel(correlation));
  }
}

export { INITIAL_MERCADOPAGO_ACTION_STATE, MERCADOPAGO_PERMISSION };
