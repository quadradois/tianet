import { randomBytes } from "node:crypto";

import { describe, expect, it, vi } from "vitest";

import { RefreshCoordinator, type BffDependencies, type FetchLike } from "@/lib/bff/backend.server";
import {
  addPermissionToPerfil,
  assignPerfilToUsuario,
  beginIamLoads,
  createPerfil,
  inactivatePerfil,
  removePerfilFromUsuario,
  removePermissionFromPerfil,
  renamePerfil,
} from "@/lib/bff/iam.server";
import type { OperationalContext } from "@/lib/bff/context.server";
import { sealSession, sessionCookieName, type BffConfig, type SessionData } from "@/lib/bff/session.server";
import { PERFIL_MANAGE_PERMISSION, PERFIL_READ_PERMISSION } from "@/lib/iam/iam-policy";

const NOW = new Date("2026-08-14T12:00:00.000Z");
const TENANT_ID = "00000000-0000-4000-8000-000000000001";
const USER_ID = "00000000-0000-4000-8000-000000000002";
const WALLET_ID = "00000000-0000-4000-8000-000000000003";
const PROFILE_ID = "00000000-0000-4000-8000-000000000004";
const TARGET_USER_ID = "00000000-0000-4000-8000-000000000005";

function config(): BffConfig {
  return { backendUrl: "http://backend.iam.invalid", origin: "http://frontend.iam.invalid", production: false, loginTenantIdentifier: "ACME", currentKeyId: "current", currentKey: randomBytes(32) };
}

const session: SessionData = {
  accessToken: "access-sensitive",
  accessTokenExpiresAt: "2026-08-14T12:15:00Z",
  refreshToken: "refresh-sensitive",
  refreshTokenExpiresAt: "2026-08-21T12:00:00Z",
  tenantId: TENANT_ID,
  userId: USER_ID,
};

function context(permissions: readonly string[]): OperationalContext {
  return {
    carteira_padrao: { id: WALLET_ID, nome: "Carteira" },
    perfil: permissions.length ? { id: PROFILE_ID, nome: "Administrador" } : null,
    permissoes: permissions,
    tenant: { id: TENANT_ID, identificador_institucional: "ACME", nome: "ACME" },
    usuario: { email: "user@example.test", id: USER_ID, nome: "Operador" },
    whatsapp: { numero: null, pareada: false },
  };
}

async function cookieStore(selected: BffConfig) {
  const encrypted = await sealSession(session, selected, NOW);
  return {
    get(name: string) { return name === sessionCookieName(selected) ? { value: encrypted } : undefined; },
    set: vi.fn(),
    delete: vi.fn(),
  };
}

function dependencies(selected: BffConfig, fetch: FetchLike, timeoutMs = 1_000): BffDependencies {
  return { config: selected, fetch, now: () => NOW, timeoutMs, refreshCoordinator: new RefreshCoordinator() };
}

function perfil(overrides: Partial<Record<string, unknown>> = {}) {
  return {
    estado: "ativo",
    id: PROFILE_ID,
    nome: "Administrador",
    permissoes: ["perfil.ler"],
    tenant_id: TENANT_ID,
    ...overrides,
  };
}

function catalogo() {
  return { itens: [{ codigo: "perfil.ler", descricao: "Ler Perfis", grupo: "perfil" }], versao: "2026-08" };
}

function efetivas(overrides: Partial<Record<string, unknown>> = {}) {
  return { perfil_id: PROFILE_ID, perfil_nome: "Administrador", permissoes: ["perfil.ler"], usuario_id: TARGET_USER_ID, ...overrides };
}

function form(values: Record<string, string>) {
  const data = new FormData();
  for (const [key, value] of Object.entries(values)) data.set(key, value);
  return data;
}

describe("BFF IAM permitido", () => {
  it("inicia GETs oficiais com Bearer, correlation e sem Idempotency-Key", async () => {
    const selected = config();
    const seen: string[] = [];
    const backend = vi.fn<FetchLike>(async (request) => {
      const url = new URL(request.url);
      seen.push(`${request.method} ${url.pathname}`);
      expect(request.headers.get("Authorization")).toBe("Bearer access-sensitive");
      expect(request.headers.get("X-Correlation-ID")).toBeTruthy();
      expect(request.headers.get("Idempotency-Key")).toBeNull();
      if (url.pathname === "/iam/permissoes") return Response.json(catalogo(), { headers: { "X-Correlation-ID": "corr-iam" } });
      if (url.pathname.endsWith("/permissoes")) return Response.json(efetivas(), { headers: { "X-Correlation-ID": "corr-iam" } });
      if (url.pathname === "/iam/perfis") return Response.json([perfil()], { headers: { "X-Correlation-ID": "corr-iam" } });
      return Response.json(perfil(), { headers: { "X-Correlation-ID": "corr-iam" } });
    });
    const loads = await beginIamLoads(
      await cookieStore(selected),
      context([PERFIL_READ_PERMISSION]),
      { perfilId: PROFILE_ID, usuarioId: TARGET_USER_ID },
      dependencies(selected, backend),
    );
    await Promise.all([loads.perfis, loads.catalogo, loads.perfil, loads.usuarioPermissoes]);
    expect(seen.sort()).toEqual([
      "GET /iam/perfis",
      `GET /iam/perfis/${PROFILE_ID}`,
      "GET /iam/permissoes",
      `GET /iam/usuarios/${TARGET_USER_ID}/permissoes`,
    ].sort());
  });

  it("nao chama backend sem permissao exata", async () => {
    const selected = config();
    const backend = vi.fn<FetchLike>();
    const loads = await beginIamLoads(await cookieStore(selected), context(["perfil.*"]), { perfilId: PROFILE_ID, usuarioId: TARGET_USER_ID }, dependencies(selected, backend));
    await expect(loads.perfis).resolves.toEqual({ kind: "denied" });
    await expect(loads.catalogo).resolves.toEqual({ kind: "denied" });
    expect(backend).not.toHaveBeenCalled();
  });

  it("rejeita payload 2xx incompleto e cross-tenant", async () => {
    const selected = config();
    const incomplete: FetchLike = async () => Response.json([{ ...perfil(), permissoes: undefined }]);
    const incompleteLoads = await beginIamLoads(await cookieStore(selected), context([PERFIL_READ_PERMISSION]), {}, dependencies(selected, incomplete));
    await expect(incompleteLoads.perfis).resolves.toMatchObject({ kind: "problem", problem: { status: 502, codigo: "resposta_backend_invalida" } });
    const crossTenant: FetchLike = async () => Response.json([{ ...perfil({ tenant_id: "00000000-0000-4000-8000-000000000999" }) }]);
    const crossLoads = await beginIamLoads(await cookieStore(selected), context([PERFIL_READ_PERMISSION]), {}, dependencies(selected, crossTenant));
    await expect(crossLoads.perfis).resolves.toMatchObject({ kind: "problem", problem: { status: 502, codigo: "resposta_backend_invalida" } });
  });

  it("mantem erros seguros e correlacionados", async () => {
    for (const status of [400, 401, 403, 404, 409, 422, 500] as const) {
      const selected = config();
      const backend: FetchLike = async () => Response.json({ codigo: "interno", mensagem: "stack cross-tenant" }, { status, headers: { "X-Correlation-ID": "corr-safe" } });
      const loads = await beginIamLoads(await cookieStore(selected), context([PERFIL_READ_PERMISSION]), { perfilId: PROFILE_ID }, dependencies(selected, backend));
      const result = await loads.perfil;
      expect(result.kind).toBe("problem");
      if (result.kind === "problem") {
        expect(result.problem.correlationId).toBeTruthy();
        expect(result.problem.mensagem).not.toContain("cross-tenant");
      }
    }
  });

  it("executa os sete comandos oficiais com Idempotency-Key", async () => {
    const selected = config();
    const seen: string[] = [];
    const backend = vi.fn<FetchLike>(async (request) => {
      const url = new URL(request.url);
      seen.push(`${request.method} ${url.pathname}`);
      expect(request.headers.get("Idempotency-Key")).toBeTruthy();
      expect(request.headers.get("Authorization")).toBe("Bearer access-sensitive");
      if (url.pathname.includes("/usuarios/")) return Response.json(efetivas(), { headers: { "X-Correlation-ID": "corr-action" } });
      return Response.json(perfil(), { status: request.method === "POST" && url.pathname === "/iam/perfis" ? 201 : 200, headers: { "X-Correlation-ID": "corr-action" } });
    });
    const cookie = await cookieStore(selected);
    const ctx = context([PERFIL_MANAGE_PERMISSION]);
    await expect(createPerfil(cookie, ctx, form({ nome: "Auditor", idempotency_key: "idem-create" }), dependencies(selected, backend))).resolves.toMatchObject({ kind: "success" });
    await expect(renamePerfil(cookie, ctx, form({ perfil_id: PROFILE_ID, nome: "Auditor Senior", idempotency_key: "idem-rename" }), dependencies(selected, backend))).resolves.toMatchObject({ kind: "success" });
    await expect(inactivatePerfil(cookie, ctx, form({ perfil_id: PROFILE_ID, idempotency_key: "idem-inactive" }), dependencies(selected, backend))).resolves.toMatchObject({ kind: "success" });
    await expect(addPermissionToPerfil(cookie, ctx, form({ perfil_id: PROFILE_ID, codigo: "perfil.ler", idempotency_key: "idem-add" }), dependencies(selected, backend))).resolves.toMatchObject({ kind: "success" });
    await expect(removePermissionFromPerfil(cookie, ctx, form({ perfil_id: PROFILE_ID, codigo: "perfil.ler", idempotency_key: "idem-remove" }), dependencies(selected, backend))).resolves.toMatchObject({ kind: "success" });
    await expect(assignPerfilToUsuario(cookie, ctx, form({ usuario_id: TARGET_USER_ID, perfil_id: PROFILE_ID, idempotency_key: "idem-assign" }), dependencies(selected, backend))).resolves.toMatchObject({ kind: "success" });
    await expect(removePerfilFromUsuario(cookie, ctx, form({ usuario_id: TARGET_USER_ID, idempotency_key: "idem-user-remove" }), dependencies(selected, backend))).resolves.toMatchObject({ kind: "success" });
    expect(seen.sort()).toEqual([
      "POST /iam/perfis",
      `PATCH /iam/perfis/${PROFILE_ID}`,
      `POST /iam/perfis/${PROFILE_ID}/inativar`,
      `PUT /iam/perfis/${PROFILE_ID}/permissoes/perfil.ler`,
      `DELETE /iam/perfis/${PROFILE_ID}/permissoes/perfil.ler`,
      `PUT /iam/usuarios/${TARGET_USER_ID}/perfil/${PROFILE_ID}`,
      `DELETE /iam/usuarios/${TARGET_USER_ID}/perfil`,
    ].sort());
  });

  it("nao chama comandos sem perfil.gerir ou codigo canonico", async () => {
    const selected = config();
    const backend = vi.fn<FetchLike>();
    await expect(createPerfil(await cookieStore(selected), context([PERFIL_READ_PERMISSION]), form({ nome: "Auditor", idempotency_key: "idem" }), dependencies(selected, backend))).resolves.toMatchObject({ kind: "problem", status: 403 });
    await expect(addPermissionToPerfil(await cookieStore(selected), context([PERFIL_MANAGE_PERMISSION]), form({ perfil_id: PROFILE_ID, codigo: "Perfil.Ler", idempotency_key: "idem" }), dependencies(selected, backend))).resolves.toMatchObject({ kind: "problem", status: 400 });
    expect(backend).not.toHaveBeenCalled();
  });
});
