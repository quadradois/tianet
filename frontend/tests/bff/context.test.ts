import { randomBytes } from "node:crypto";

import { describe, expect, it, vi } from "vitest";

import { ApiProblem, RefreshCoordinator, type BffDependencies, type FetchLike } from "@/lib/bff/backend.server";
import { handleContextBootstrap, loadOperationalContext } from "@/lib/bff/context.server";
import {
  sealSession,
  sessionCookieName,
  type BffConfig,
  type CookieStore,
  type SessionCookieOptions,
  type SessionData,
} from "@/lib/bff/session.server";

const NOW = new Date("2026-08-13T12:00:00.000Z");
const CORRELATION = "corr-context-289";

function config(): BffConfig {
  return {
    backendUrl: "http://backend.context.invalid",
    origin: "http://frontend.context.invalid",
    production: false,
    loginTenantIdentifier: "ACME",
    currentKeyId: "current",
    currentKey: randomBytes(32),
  };
}

function session(): SessionData {
  return {
    accessToken: "access-old",
    accessTokenExpiresAt: "2026-08-13T12:15:00.000Z",
    refreshToken: "refresh-sensitive",
    refreshTokenExpiresAt: "2026-08-20T12:00:00.000Z",
    tenantId: "tenant-1",
    userId: "user-1",
  };
}

const operationalContext = {
  carteira_padrao: { id: "wallet-1", nome: "Carteira Centro" },
  perfil: null,
  permissoes: [],
  tenant: { id: "tenant-1", identificador_institucional: "ACME", nome: "Instituicao ACME" },
  usuario: { email: "user@example.test", id: "user-1", nome: "Operador" },
  whatsapp: { alerta_queda_ativa: false, numero: null, pareada: false, queda_detectada_em: null },
};

class MemoryCookies implements CookieStore {
  readonly values = new Map<string, string>();
  get(name: string): { value: string } | undefined {
    const value = this.values.get(name);
    return value === undefined ? undefined : { value };
  }
  set(name: string, value: string, options: SessionCookieOptions): void {
    void options;
    this.values.set(name, value);
  }
}

function dependencies(fetch: FetchLike, selectedConfig = config()): BffDependencies {
  return { config: selectedConfig, fetch, now: () => NOW, timeoutMs: 1_000, refreshCoordinator: new RefreshCoordinator() };
}

async function cookiesWithSession(selectedConfig: BffConfig): Promise<MemoryCookies> {
  const cookies = new MemoryCookies();
  cookies.values.set(sessionCookieName(selectedConfig), await sealSession(session(), selectedConfig, NOW));
  return cookies;
}

function bootstrapRequest(origin = "http://frontend.context.invalid"): Request {
  return new Request("http://frontend.context.invalid/api/auth/bootstrap", {
    method: "POST",
    headers: { Origin: origin, "Sec-Fetch-Site": "same-origin", "X-Correlation-ID": CORRELATION, "X-CSRF-Protection": "1" },
  });
}

describe("contexto operacional server-side", () => {
  it("consulta somente o proprio Principal e aceita perfil nulo", async () => {
    const selectedConfig = config();
    const cookies = await cookiesWithSession(selectedConfig);
    const backend = vi.fn<FetchLike>(async (request) => {
      expect(request.url).toBe("http://backend.context.invalid/iam/contexto-atual");
      expect(request.method).toBe("GET");
      expect(request.headers.get("Authorization")).toBe("Bearer access-old");
      expect(request.url).not.toMatch(/usuario|tenant|carteira/);
      return Response.json(operationalContext, { headers: { "X-Correlation-ID": CORRELATION } });
    });
    await expect(loadOperationalContext(cookies, dependencies(backend, selectedConfig), CORRELATION)).resolves.toEqual(operationalContext);
    expect(backend).toHaveBeenCalledOnce();
  });

  it("rejeita resposta 200 malformada e nao fabrica Carteira", async () => {
    const selectedConfig = config();
    const cookies = await cookiesWithSession(selectedConfig);
    const backend: FetchLike = async () => Response.json({ ...operationalContext, carteira_padrao: null });
    await expect(loadOperationalContext(cookies, dependencies(backend, selectedConfig), CORRELATION))
      .rejects.toMatchObject({ status: 502, codigo: "resposta_backend_invalida" });
    const permissionsWithoutProfile: FetchLike = async () => Response.json({
      ...operationalContext,
      permissoes: ["devedor.ler"],
    });
    await expect(loadOperationalContext(cookies, dependencies(permissionsWithoutProfile, selectedConfig), CORRELATION))
      .rejects.toMatchObject({ status: 502, codigo: "resposta_backend_invalida" });
  });

  it("rejeita contexto de Usuario ou Tenant diferente da sessao", async () => {
    const selectedConfig = config();
    const cookies = await cookiesWithSession(selectedConfig);
    for (const payload of [
      { ...operationalContext, usuario: { ...operationalContext.usuario, id: "user-cross-tenant" } },
      { ...operationalContext, tenant: { ...operationalContext.tenant, id: "tenant-cross-tenant" } },
    ]) {
      const backend: FetchLike = async () => Response.json(payload);
      await expect(loadOperationalContext(cookies, dependencies(backend, selectedConfig), CORRELATION))
        .rejects.toMatchObject({ status: 502, codigo: "resposta_backend_invalida" });
    }
    const bootstrapBackend: FetchLike = async () => Response.json({
      ...operationalContext,
      tenant: { ...operationalContext.tenant, id: "tenant-cross-tenant" },
    });
    const response = await handleContextBootstrap(
      bootstrapRequest(),
      await cookiesWithSession(selectedConfig),
      dependencies(bootstrapBackend, selectedConfig),
    );
    expect(response.status).toBe(502);
  });

  it("preserva 409 de contexto incompleto sem escolher fallback", async () => {
    const selectedConfig = config();
    const cookies = await cookiesWithSession(selectedConfig);
    const backend: FetchLike = async () => Response.json(
      { codigo: "contexto_operacional_incompleto", mensagem: "Contexto operacional corrente indisponivel." },
      { status: 409, headers: { "X-Correlation-ID": CORRELATION } },
    );
    await expect(loadOperationalContext(cookies, dependencies(backend, selectedConfig), CORRELATION))
      .rejects.toMatchObject({ status: 409, codigo: "contexto_operacional_incompleto" });
  });

  it("mapeia status nao certificado e detalhe interno para 502 seguro", async () => {
    const selectedConfig = config();
    const cookies = await cookiesWithSession(selectedConfig);
    for (const status of [400, 403, 404, 422]) {
      const backend: FetchLike = async () => Response.json(
        { codigo: "nao_contratado", mensagem: "segredo interno" },
        { status, headers: { "X-Correlation-ID": CORRELATION } },
      );
      await expect(loadOperationalContext(cookies, dependencies(backend, selectedConfig), CORRELATION))
        .rejects.toMatchObject({ status: 502, codigo: "resposta_backend_invalida", correlationId: CORRELATION });
    }
    const bootstrapBackend: FetchLike = async () => Response.json(
      { codigo: "nao_contratado", mensagem: "segredo interno" },
      { status: 403, headers: { "X-Correlation-ID": CORRELATION } },
    );
    const response = await handleContextBootstrap(
      bootstrapRequest(),
      await cookiesWithSession(selectedConfig),
      dependencies(bootstrapBackend, selectedConfig),
    );
    expect(response.status).toBe(502);
    await expect(response.json()).resolves.toMatchObject({
      codigo: "resposta_backend_invalida",
      correlationId: CORRELATION,
    });
  });

  it("sanitiza 500 certificado e preserva correlation", async () => {
    const selectedConfig = config();
    const cookies = await cookiesWithSession(selectedConfig);
    const backend: FetchLike = async () => Response.json(
      { codigo: "interno", mensagem: "stack secreta" },
      { status: 500, headers: { "X-Correlation-ID": CORRELATION } },
    );
    await expect(loadOperationalContext(cookies, dependencies(backend, selectedConfig), CORRELATION))
      .rejects.toMatchObject({ status: 500, codigo: "erro_tecnico", correlationId: CORRELATION });
  });

  it("timeout do contexto retorna 504 seguro e correlacionado", async () => {
    const selectedConfig = config();
    const cookies = await cookiesWithSession(selectedConfig);
    const backend: FetchLike = async (request) => new Promise((_, reject) => {
      request.signal.addEventListener("abort", () => reject(request.signal.reason), { once: true });
    });
    await expect(loadOperationalContext(cookies, { ...dependencies(backend, selectedConfig), timeoutMs: 5 }, CORRELATION))
      .rejects.toMatchObject({ status: 504, codigo: "timeout_backend", correlationId: CORRELATION });
  });

  it("bootstrap protegido faz um refresh, reconsulta e persiste a sessao", async () => {
    const selectedConfig = config();
    const cookies = await cookiesWithSession(selectedConfig);
    let contextCalls = 0;
    const backend = vi.fn<FetchLike>(async (request) => {
      const url = new URL(request.url);
      if (url.pathname === "/auth/refresh") {
        return Response.json({ access_token: "access-new", access_token_expira_em: "2026-08-13T12:30:00.000Z", tenant_id: "tenant-1", token_type: "bearer", usuario_id: "user-1" });
      }
      contextCalls += 1;
      if (contextCalls === 1) return Response.json({ codigo: "autenticacao_recusada", mensagem: "recusada" }, { status: 401 });
      expect(request.headers.get("Authorization")).toBe("Bearer access-new");
      return Response.json(operationalContext, { headers: { "X-Correlation-ID": CORRELATION } });
    });
    const response = await handleContextBootstrap(bootstrapRequest(), cookies, dependencies(backend, selectedConfig));
    expect(response.status).toBe(204);
    expect(contextCalls).toBe(2);
    expect(cookies.values.get(sessionCookieName(selectedConfig))).not.toContain("access-new");
  });

  it("recusa Origin hostil antes de consultar backend", async () => {
    const selectedConfig = config();
    const cookies = await cookiesWithSession(selectedConfig);
    const backend = vi.fn<FetchLike>();
    const response = await handleContextBootstrap(bootstrapRequest("http://hostil.invalid"), cookies, dependencies(backend, selectedConfig));
    expect(response.status).toBe(403);
    expect(backend).not.toHaveBeenCalled();
  });

  it("aceita alerta de queda ativo somente com timestamp ISO date-time valido", async () => {
    const selectedConfig = config();
    const cookies = await cookiesWithSession(selectedConfig);
    for (const queda_detectada_em of [
      "2026-09-08T12:00:00.000Z",
      "2026-09-08T09:00:00-03:00",
      "2026-09-08T09:00:00.123456789-03:00",
      "2024-02-29T12:00:00Z",
    ]) {
      const ativo = {
        ...operationalContext,
        whatsapp: { alerta_queda_ativa: true, numero: null, pareada: false, queda_detectada_em },
      };
      const backend: FetchLike = async () => Response.json(ativo);
      await expect(loadOperationalContext(cookies, dependencies(backend, selectedConfig), CORRELATION)).resolves.toEqual(ativo);
    }
  });

  it("rejeita alerta de queda inconsistente, mal tipado ou com data invalida", async () => {
    const selectedConfig = config();
    const cookies = await cookiesWithSession(selectedConfig);
    const inconsistentes: unknown[] = [
      // Ativo exige timestamp: null nao e queda datada.
      { alerta_queda_ativa: true, numero: null, pareada: false, queda_detectada_em: null },
      // Inativo exige null: timestamp com alerta apagado e contradicao.
      { alerta_queda_ativa: false, numero: null, pareada: false, queda_detectada_em: "2026-09-08T12:00:00.000Z" },
      // Tipos errados.
      { alerta_queda_ativa: "true", numero: null, pareada: false, queda_detectada_em: null },
      { alerta_queda_ativa: false, numero: null, pareada: false, queda_detectada_em: 123 },
      // Data invalida ou fora do ISO date-time.
      { alerta_queda_ativa: true, numero: null, pareada: false, queda_detectada_em: "08/09/2026" },
      { alerta_queda_ativa: true, numero: null, pareada: false, queda_detectada_em: "2026-09-08" },
      { alerta_queda_ativa: true, numero: null, pareada: false, queda_detectada_em: "2026-13-40T99:99:99Z" },
      { alerta_queda_ativa: true, numero: null, pareada: false, queda_detectada_em: "nao-uma-data" },
      // Calendariamente impossivel: Date.parse transborda fev/30 para marco.
      { alerta_queda_ativa: true, numero: null, pareada: false, queda_detectada_em: "2026-02-30T12:00:00Z" },
      // 2026 nao e bissexto: 29 de fevereiro nao existe.
      { alerta_queda_ativa: true, numero: null, pareada: false, queda_detectada_em: "2026-02-29T12:00:00Z" },
      // Abril tem 30 dias.
      { alerta_queda_ativa: true, numero: null, pareada: false, queda_detectada_em: "2026-04-31T12:00:00Z" },
      // Segundos obrigatorios no RFC 3339 estrito.
      { alerta_queda_ativa: true, numero: null, pareada: false, queda_detectada_em: "2026-09-08T12:00Z" },
      // Offset exige dois-pontos.
      { alerta_queda_ativa: true, numero: null, pareada: false, queda_detectada_em: "2026-09-08T12:00:00+0300" },
      // Faixas de hora e offset.
      { alerta_queda_ativa: true, numero: null, pareada: false, queda_detectada_em: "2026-09-08T24:00:00Z" },
      { alerta_queda_ativa: true, numero: null, pareada: false, queda_detectada_em: "2026-09-08T12:00:00+24:00" },
      // Campos obrigatorios ausentes nao podem passar como inativos.
      { numero: null, pareada: false, queda_detectada_em: null },
      { alerta_queda_ativa: false, numero: null, pareada: false },
    ];
    for (const whatsapp of inconsistentes) {
      const backend: FetchLike = async () => Response.json({ ...operationalContext, whatsapp });
      await expect(loadOperationalContext(cookies, dependencies(backend, selectedConfig), CORRELATION))
        .rejects.toMatchObject({ status: 502, codigo: "resposta_backend_invalida" });
    }
  });

  it("sem cookie produz 401 seguro", async () => {
    await expect(loadOperationalContext(new MemoryCookies(), dependencies(async () => new Response()), CORRELATION))
      .rejects.toBeInstanceOf(ApiProblem);
  });
});
