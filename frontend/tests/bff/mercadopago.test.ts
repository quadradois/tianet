import { randomBytes } from "node:crypto";

import { describe, expect, it, vi } from "vitest";

import type { BffDependencies, FetchLike } from "@/lib/bff/backend.server";
import type { OperationalContext } from "@/lib/bff/context.server";
import {
  disableMercadoPago,
  enableMercadoPago,
  readMercadoPagoConfig,
  saveMercadoPagoCredentials,
  testMercadoPagoCredentials,
} from "@/lib/bff/mercadopago.server";
import { sealSession, SESSION_COOKIE_NAME, type BffConfig, type CookieStore, type SessionCookieOptions } from "@/lib/bff/session.server";

const NOW = new Date("2026-09-22T12:00:00.000Z");
const TOKEN = "APP_USR-token-de-producao";
const SECRET = "segredo-do-webhook";
const CHAVE = "11111111-1111-4111-8111-111111111111";
const config: BffConfig = { backendUrl: "http://backend.test", origin: "http://frontend.test", production: true, loginTenantIdentifier: "ACME", currentKeyId: "current", currentKey: randomBytes(32) };
const base: OperationalContext = {
  carteira_padrao: { id: "wallet", nome: "Carteira" },
  perfil: { id: "profile", nome: "Administrador" },
  permissoes: ["mercadopago.configurar"],
  tenant: { id: "tenant", identificador_institucional: "ACME", nome: "ACME" },
  usuario: { id: "user", nome: "Operador", email: "operador@example.test" },
  whatsapp: { alerta_queda_ativa: false, numero: null, pareada: false, queda_detectada_em: null },
};

const DESLIGADO = {
  tenant_id: "tenant",
  habilitado: false,
  credencial_configurada: false,
  assinatura_configurada: false,
  testado_em: null,
  atualizado_em: "2026-09-22T12:00:00Z",
  atualizado_por: null,
};

class MemoryCookies implements CookieStore {
  values = new Map<string, string>();
  get(name: string) { const value = this.values.get(name); return value === undefined ? undefined : { value }; }
  set(name: string, value: string, options: SessionCookieOptions) { void options; this.values.set(name, value); }
}

async function setup(fetch: FetchLike) {
  const cookies = new MemoryCookies();
  cookies.values.set(SESSION_COOKIE_NAME, await sealSession({ accessToken: "access", accessTokenExpiresAt: "2099-01-01T00:00:00Z", refreshToken: "refresh", refreshTokenExpiresAt: "2099-01-02T00:00:00Z", tenantId: "tenant", userId: "user" }, config, NOW));
  const dependencies: BffDependencies = { config, fetch, now: () => NOW };
  return { cookies, dependencies };
}

function json(body: unknown, status = 200) { return Response.json(body, { status, headers: { "X-Correlation-ID": "corr-mp" } }); }

function form(entries: Record<string, string>): FormData {
  const data = new FormData();
  for (const [key, value] of Object.entries(entries)) data.set(key, value);
  return data;
}

describe("BFF do recebimento por Pix", () => {
  it("le a configuracao e devolve o estado desligado", async () => {
    const fetch = vi.fn<FetchLike>(async () => json(DESLIGADO));
    const { cookies, dependencies } = await setup(fetch);

    const resultado = await readMercadoPagoConfig(cookies, base, dependencies);

    expect(resultado.kind).toBe("ready");
    if (resultado.kind === "ready") expect(resultado.config.habilitado).toBe(false);
  });

  it("nega leitura sem a permissao, sem chamar o backend", async () => {
    const fetch = vi.fn<FetchLike>(async () => json(DESLIGADO));
    const { cookies, dependencies } = await setup(fetch);

    const resultado = await readMercadoPagoConfig(cookies, { ...base, permissoes: [] }, dependencies);

    expect(resultado).toMatchObject({ kind: "problem", status: 403 });
    expect(fetch).not.toHaveBeenCalled();
  });

  it("envia as credenciais com Idempotency-Key e nao as devolve no estado", async () => {
    const backend = vi.fn<FetchLike>(async () => json({ ...DESLIGADO, credencial_configurada: true, assinatura_configurada: true }));
    const { cookies, dependencies } = await setup(backend);

    const resultado = await saveMercadoPagoCredentials(cookies, base, dependencies, form({ credencial: TOKEN, assinatura: SECRET, idempotency_key: CHAVE }));

    expect(resultado.kind).toBe("success");
    // O segredo entra e NAO volta: nem o backend devolve, nem o estado carrega.
    expect(JSON.stringify(resultado)).not.toContain(TOKEN);
    expect(JSON.stringify(resultado)).not.toContain(SECRET);
    const request = backend.mock.calls[0]?.[0] as Request | undefined;
    if (!request) throw new Error("requisicao ausente");
    expect(request.method).toBe("PUT");
    expect(new URL(request.url).pathname).toBe("/platform/mercadopago/configuracao");
    expect(request.headers.get("Idempotency-Key")).toBe(CHAVE);
  });

  it("recusa credencial curta antes de chamar o backend", async () => {
    const fetch = vi.fn<FetchLike>(async () => json(DESLIGADO));
    const { cookies, dependencies } = await setup(fetch);

    const resultado = await saveMercadoPagoCredentials(cookies, base, dependencies, form({ access_token: "curto", assinatura: SECRET, idempotency_key: CHAVE }));

    expect(resultado).toMatchObject({ kind: "problem", status: 400 });
    expect(fetch).not.toHaveBeenCalled();
  });

  it("propaga o 422 do backend quando ligar sem teste", async () => {
    const fetch = vi.fn<FetchLike>(async () => json({ codigo: "regra_violada", mensagem: "teste obrigatorio" }, 422));
    const { cookies, dependencies } = await setup(fetch);

    const resultado = await enableMercadoPago(cookies, base, dependencies, form({ idempotency_key: CHAVE }));

    expect(resultado).toMatchObject({ kind: "problem", status: 422 });
  });

  it("testar e desligar nomeiam a operacao que produziu o sucesso", async () => {
    const fetch = vi.fn<FetchLike>(async () => json({ ...DESLIGADO, credencial_configurada: true, assinatura_configurada: true, testado_em: "2026-09-22T12:00:00Z" }));
    const { cookies, dependencies } = await setup(fetch);

    const testado = await testMercadoPagoCredentials(cookies, base, dependencies, form({ idempotency_key: CHAVE }));
    const desligado = await disableMercadoPago(cookies, base, dependencies, form({ idempotency_key: CHAVE }));

    expect(testado).toMatchObject({ kind: "success", operacao: "testar" });
    expect(desligado).toMatchObject({ kind: "success", operacao: "desabilitar" });
  });

  it("resposta sem o formato esperado vira indisponibilidade, nao sucesso", async () => {
    const fetch = vi.fn<FetchLike>(async () => json({ qualquer: "coisa" }));
    const { cookies, dependencies } = await setup(fetch);

    const resultado = await readMercadoPagoConfig(cookies, base, dependencies);

    expect(resultado).toMatchObject({ kind: "problem", status: 502 });
  });
});
