import { randomBytes } from "node:crypto";

import { describe, expect, it, vi } from "vitest";

import { RefreshCoordinator, type BffDependencies, type FetchLike } from "@/lib/bff/backend.server";
import type { OperationalContext } from "@/lib/bff/context.server";
import {
  createDevedor,
  getDevedor,
  getDevedorHistory,
  inactivateDevedor,
  listDevedores,
  reactivateDevedor,
  updateDevedor,
} from "@/lib/bff/devedores.server";
import { sealSession, sessionCookieName, type BffConfig, type SessionData } from "@/lib/bff/session.server";
import type { DevedorListFilters } from "@/lib/devedores/devedores-policy";

const NOW = new Date("2026-08-14T12:00:00.000Z");
const TENANT_ID = "00000000-0000-4000-8000-000000000001";
const USER_ID = "00000000-0000-4000-8000-000000000002";
const WALLET_ID = "00000000-0000-4000-8000-000000000003";
const PROFILE_ID = "00000000-0000-4000-8000-000000000004";
const DEBTOR_ID = "00000000-0000-4000-8000-000000000010";
const OTHER_WALLET = "00000000-0000-4000-8000-000000000099";

function config(): BffConfig {
  return { backendUrl: "http://backend.devedores.invalid", origin: "http://frontend.devedores.invalid", production: false, loginTenantIdentifier: "ACME", currentKeyId: "current", currentKey: randomBytes(32) };
}

const session: SessionData = { accessToken: "access-sensitive", accessTokenExpiresAt: "2026-08-14T12:15:00Z", refreshToken: "refresh-sensitive", refreshTokenExpiresAt: "2026-08-21T12:00:00Z", tenantId: TENANT_ID, userId: USER_ID };

function context(permissions: readonly string[]): OperationalContext {
  return { carteira_padrao: { id: WALLET_ID, nome: "Carteira" }, perfil: permissions.length ? { id: PROFILE_ID, nome: "Operador" } : null, permissoes: permissions, tenant: { id: TENANT_ID, identificador_institucional: "ACME", nome: "ACME" }, whatsapp: { numero: null, pareada: false }, usuario: { email: "user@example.test", id: USER_ID, nome: "Operador" } };
}

async function cookieStore(selected: BffConfig) {
  const values = new Map<string, string>();
  values.set(sessionCookieName(selected), await sealSession(session, selected, NOW));
  return {
    get(name: string) { const value = values.get(name); return value ? { value } : undefined; },
    set(name: string, value: string) { values.set(name, value); },
  };
}

function dependencies(selected: BffConfig, fetch: FetchLike, timeoutMs = 1_000): BffDependencies {
  return { config: selected, fetch, now: () => NOW, timeoutMs, refreshCoordinator: new RefreshCoordinator() };
}

const filters: DevedorListFilters = { page: 1, size: 20 };

function devedor(carteira_id = WALLET_ID) {
  return { atualizado_em: null, carteira_id, contatos: [{ preferencial: true, tipo: "email", valor: "cliente@example.test" }], criado_em: "2026-08-14T10:00:00Z", documento: "12345678909", estado: "ativo", id: DEBTOR_ID, nome: "Cliente Devedor" };
}

describe("BFF Devedores", () => {
  it("lista e consulta por documento usando somente Carteira propria", async () => {
    const selected = config();
    const seen: URL[] = [];
    const backend = vi.fn<FetchLike>(async (request) => {
      const url = new URL(request.url);
      seen.push(url);
      expect(request.headers.get("Authorization")).toBe("Bearer access-sensitive");
      expect(request.cache).toBe("no-store");
      return Response.json(url.searchParams.get("documento") ? devedor() : { items: [devedor()], page: 1, pages: 1, size: 20, total: 1 }, { headers: { "X-Correlation-ID": "corr-list" } });
    });
    const listed = await listDevedores(await cookieStore(selected), context(["devedor.ler"]), filters, dependencies(selected, backend));
    const found = await listDevedores(await cookieStore(selected), context(["devedor.ler"]), { ...filters, documento: "12345678909" }, dependencies(selected, backend));
    expect(listed.kind).toBe("ready");
    expect(found.kind).toBe("ready");
    expect(seen.map((url) => url.pathname)).toEqual([`/credit/carteiras/${WALLET_ID}/devedores`, `/credit/carteiras/${WALLET_ID}/devedores`]);
    expect(seen[1]?.searchParams.get("documento")).toBe("12345678909");
    expect(seen.every((url) => !url.searchParams.has("tenant_id") && !url.searchParams.has("carteira_id"))).toBe(true);
  });

  it("nao chama backend sem permissao exata", async () => {
    const selected = config();
    const backend = vi.fn<FetchLike>();
    await expect(listDevedores(await cookieStore(selected), context(["devedor.*"]), filters, dependencies(selected, backend))).resolves.toEqual({ kind: "denied" });
    await expect(getDevedor(await cookieStore(selected), context([]), DEBTOR_ID, dependencies(selected, backend))).resolves.toEqual({ kind: "denied" });
    expect(backend).not.toHaveBeenCalled();
  });

  it("rejeita 200 incompleto ou de outra Carteira sem fabricar empty", async () => {
    const selected = config();
    const missing = await listDevedores(await cookieStore(selected), context(["devedor.ler"]), filters, dependencies(selected, async () => Response.json({ items: [{ ...devedor(), contatos: undefined }], page: 1, pages: 1, size: 20, total: 1 })));
    expect(missing).toMatchObject({ kind: "problem", problem: { status: 502, codigo: "resposta_backend_invalida" } });
    const cross = await getDevedor(await cookieStore(selected), context(["devedor.ler"]), DEBTOR_ID, dependencies(selected, async () => Response.json(devedor(OTHER_WALLET))));
    expect(cross).toMatchObject({ kind: "problem", problem: { status: 502, codigo: "resposta_backend_invalida" } });
  });

  it("mapeia 400, 403, 404, 409, 422 e 5xx com correlation e 404 neutro", async () => {
    for (const [status, expected] of [[400, "payload_invalido"], [403, "acesso_negado"], [404, "recurso_indisponivel"], [409, "devedor_ja_existe"], [422, "regra_violada"], [500, "erro_tecnico"]] as const) {
      const selected = config();
      const result = await listDevedores(await cookieStore(selected), context(["devedor.ler"]), filters, dependencies(selected, async () => Response.json({ codigo: expected, mensagem: "stack cross-carteira" }, { status, headers: { "X-Correlation-ID": "corr-safe" } })));
      expect(result.kind).toBe("problem");
      if (result.kind === "problem") {
        expect(result.problem.correlationId).toBe("corr-safe");
        expect(result.problem.codigo).toBe(expected);
        expect(result.problem.mensagem).not.toContain("cross-carteira");
      }
    }
  });

  it("consulta detalhe e historico por ID oficial", async () => {
    const selected = config();
    const paths: string[] = [];
    const backend: FetchLike = async (request) => {
      const url = new URL(request.url);
      paths.push(url.pathname);
      if (url.pathname.endsWith("/historico")) return Response.json({ devedor_id: DEBTOR_ID, eventos: [{ acao: "criar.sucesso", criado_em: "2026-08-14T10:00:00Z", detalhes: null, status: "sucesso" }] });
      return Response.json(devedor());
    };
    await expect(getDevedor(await cookieStore(selected), context(["devedor.ler"]), DEBTOR_ID, dependencies(selected, backend))).resolves.toMatchObject({ kind: "ready" });
    await expect(getDevedorHistory(await cookieStore(selected), context(["devedor.ler"]), DEBTOR_ID, dependencies(selected, backend))).resolves.toMatchObject({ kind: "ready" });
    expect(paths).toEqual([`/credit/carteiras/${WALLET_ID}/devedores/${DEBTOR_ID}`, `/credit/carteiras/${WALLET_ID}/devedores/${DEBTOR_ID}/historico`]);
  });

  it("envia comandos com Idempotency-Key e sem Carteira do formulario", async () => {
    const selected = config();
    const calls: Request[] = [];
    const backend: FetchLike = async (request) => { calls.push(request); return Response.json(devedor(), { status: request.method === "POST" && new URL(request.url).pathname.endsWith("/devedores") ? 201 : 200, headers: { "X-Correlation-ID": "corr-command" } }); };
    const form = new FormData();
    form.set("documento", "12345678909");
    form.set("nome", "Cliente");
    form.set("contato_tipo", "email");
    form.set("contato_valor", "cliente@example.test");
    form.set("carteira_id", OTHER_WALLET);
    await expect(createDevedor(await cookieStore(selected), context(["devedor.criar"]), form, dependencies(selected, backend))).resolves.toMatchObject({ kind: "success" });
    form.set("devedor_id", DEBTOR_ID);
    await expect(updateDevedor(await cookieStore(selected), context(["devedor.atualizar"]), DEBTOR_ID, form, dependencies(selected, backend))).resolves.toMatchObject({ kind: "success" });
    await expect(inactivateDevedor(await cookieStore(selected), context(["devedor.inativar"]), DEBTOR_ID, dependencies(selected, backend))).resolves.toMatchObject({ kind: "success" });
    await expect(reactivateDevedor(await cookieStore(selected), context(["devedor.reativar"]), DEBTOR_ID, dependencies(selected, backend))).resolves.toMatchObject({ kind: "success" });
    expect(calls).toHaveLength(4);
    expect(calls.every((request) => request.headers.get("Idempotency-Key"))).toBe(true);
    expect(calls.map((request) => new URL(request.url).pathname)).toEqual([
      `/credit/carteiras/${WALLET_ID}/devedores`,
      `/credit/carteiras/${WALLET_ID}/devedores/${DEBTOR_ID}`,
      `/credit/carteiras/${WALLET_ID}/devedores/${DEBTOR_ID}/inativar`,
      `/credit/carteiras/${WALLET_ID}/devedores/${DEBTOR_ID}/reativar`,
    ]);
  });
});
