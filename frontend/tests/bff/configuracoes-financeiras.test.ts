import { randomBytes } from "node:crypto";

import { describe, expect, it, vi } from "vitest";

import { RefreshCoordinator, type BffDependencies, type FetchLike } from "@/lib/bff/backend.server";
import {
  activateConfiguracao,
  approveConfiguracao,
  beginConfiguracoesLoads,
  captureSnapshot,
  createCalendario,
  createConfiguracao,
  createModalidade,
  inactivateConfiguracao,
  programConfiguracao,
} from "@/lib/bff/configuracoes-financeiras.server";
import type { OperationalContext } from "@/lib/bff/context.server";
import { sealSession, sessionCookieName, type BffConfig, type SessionData } from "@/lib/bff/session.server";
import {
  CALENDARIO_MANAGE_PERMISSION,
  CONFIGURACOES_ACTIVATE_PERMISSION,
  CONFIGURACOES_APPROVE_PERMISSION,
  CONFIGURACOES_MANAGE_PERMISSION,
  CONFIGURACOES_READ_PERMISSION,
  MODALIDADE_MANAGE_PERMISSION,
  SNAPSHOT_CAPTURE_PERMISSION,
} from "@/lib/configuracoes-financeiras/configuracoes-policy";

const NOW = new Date("2026-08-14T12:00:00.000Z");
const TENANT_ID = "00000000-0000-4000-8000-000000000001";
const USER_ID = "00000000-0000-4000-8000-000000000002";
const WALLET_ID = "00000000-0000-4000-8000-000000000003";
const PROFILE_ID = "00000000-0000-4000-8000-000000000004";
const CONFIG_ID = "00000000-0000-4000-8000-000000000100";
const CALENDAR_ID = "00000000-0000-4000-8000-000000000101";
const MODALIDADE_ID = "00000000-0000-4000-8000-000000000102";

function config(): BffConfig {
  return { backendUrl: "http://backend.configuracoes.invalid", origin: "http://frontend.configuracoes.invalid", production: false, loginTenantIdentifier: "ACME", currentKeyId: "current", currentKey: randomBytes(32) };
}

const session: SessionData = { accessToken: "access-sensitive", accessTokenExpiresAt: "2026-08-14T12:15:00Z", refreshToken: "refresh-sensitive", refreshTokenExpiresAt: "2026-08-21T12:00:00Z", tenantId: TENANT_ID, userId: USER_ID };

function context(permissions: readonly string[]): OperationalContext {
  return { carteira_padrao: { id: WALLET_ID, nome: "Carteira" }, perfil: permissions.length ? { id: PROFILE_ID, nome: "Operador" } : null, permissoes: permissions, tenant: { id: TENANT_ID, identificador_institucional: "ACME", nome: "ACME" }, usuario: { email: "user@example.test", id: USER_ID, nome: "Operador" } };
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

function configuracao() {
  return {
    aprovada_em: null,
    aprovada_por_usuario_id: null,
    atualizada_em: null,
    calendario_id: CALENDAR_ID,
    carteira_id: WALLET_ID,
    criada_em: "2026-08-14T12:00:00Z",
    criada_por_usuario_id: USER_ID,
    estado: "rascunho",
    id: CONFIG_ID,
    modalidade: "consignado",
    parametros: { limite: "opaco" },
    tenant_id: TENANT_ID,
    total_eventos: 1,
    versao: 1,
    vigencia_fim: null,
    vigencia_inicio: "2026-08-14",
  };
}

function modalidade() {
  return { ativa: true, carteira_id: WALLET_ID, codigo: "consignado", id: MODALIDADE_ID, nome: "Consignado", tenant_id: TENANT_ID };
}

function calendario() {
  return { carteira_id: WALLET_ID, codigo: "br", feriados: ["2026-01-01"], id: CALENDAR_ID, nome: "Brasil", tenant_id: TENANT_ID };
}

function snapshot() {
  return { capturado_em: "2026-08-14T12:00:00Z", capturado_por_usuario_id: USER_ID, carteira_id: WALLET_ID, configuracao_id: CONFIG_ID, hash_parametros: "sha256:opaco", modalidade: "consignado", motivo: null, parametros: { limite: "opaco" }, tenant_id: TENANT_ID, versao: 1 };
}

function form(values: Record<string, string>) {
  const data = new FormData();
  for (const [key, value] of Object.entries(values)) data.set(key, value);
  return data;
}

describe("BFF de Configuracoes Financeiras", () => {
  it("inicia os quatro GETs oficiais com Carteira propria, correlation e sem Idempotency-Key", async () => {
    const selected = config();
    const seen: URL[] = [];
    const backend = vi.fn<FetchLike>(async (request) => {
      const url = new URL(request.url);
      seen.push(url);
      expect(request.headers.get("Authorization")).toBe("Bearer access-sensitive");
      expect(request.headers.get("X-Correlation-ID")).toBeTruthy();
      expect(request.headers.get("Idempotency-Key")).toBeNull();
      expect(request.cache).toBe("no-store");
      if (url.pathname.endsWith("/vigente")) return Response.json({ carteira_id: WALLET_ID, configuracao_id: CONFIG_ID, consultada_em: "2026-08-14T12:00:00Z", modalidade: "consignado", parametros: { limite: "opaco" }, tenant_id: TENANT_ID, versao: 1 }, { headers: { "X-Correlation-ID": "corr-config" } });
      if (url.pathname.endsWith("/modalidades")) return Response.json([modalidade()], { headers: { "X-Correlation-ID": "corr-config" } });
      if (url.pathname.endsWith("/calendarios")) return Response.json([calendario()], { headers: { "X-Correlation-ID": "corr-config" } });
      return Response.json([configuracao()], { headers: { "X-Correlation-ID": "corr-config" } });
    });
    const loads = await beginConfiguracoesLoads(await cookieStore(selected), context([CONFIGURACOES_READ_PERMISSION]), { dataReferencia: "2026-08-14", modalidade: "consignado" }, dependencies(selected, backend));
    await Promise.all([loads.configuracoes, loads.vigente, loads.modalidades, loads.calendarios]);
    expect(backend).toHaveBeenCalledTimes(4);
    expect(seen.map((url) => url.pathname).sort()).toEqual([
      "/credit/configuracoes-financeiras",
      "/credit/configuracoes-financeiras/calendarios",
      "/credit/configuracoes-financeiras/modalidades",
      "/credit/configuracoes-financeiras/vigente",
    ]);
    expect(seen.find((url) => url.pathname === "/credit/configuracoes-financeiras")?.searchParams.get("carteira_id")).toBe(WALLET_ID);
  });

  it("nao chama backend sem permissao exata", async () => {
    const selected = config();
    const backend = vi.fn<FetchLike>();
    const loads = await beginConfiguracoesLoads(await cookieStore(selected), context(["configuracoes_financeiras.configuracao.*"]), {}, dependencies(selected, backend));
    await expect(loads.configuracoes).resolves.toEqual({ kind: "denied" });
    await expect(loads.vigente).resolves.toEqual({ kind: "denied" });
    expect(backend).not.toHaveBeenCalled();
  });

  it("rejeita 2xx inesperado, payload incompleto e cross-carteira", async () => {
    const selected = config();
    const created: FetchLike = async () => Response.json([configuracao()], { status: 201 });
    const createdLoads = await beginConfiguracoesLoads(await cookieStore(selected), context([CONFIGURACOES_READ_PERMISSION]), {}, dependencies(selected, created));
    await expect(createdLoads.configuracoes).resolves.toMatchObject({ kind: "problem", problem: { status: 502, codigo: "resposta_backend_invalida" } });
    const incomplete: FetchLike = async () => Response.json([{ ...configuracao(), calendario_id: undefined }]);
    const incompleteLoads = await beginConfiguracoesLoads(await cookieStore(selected), context([CONFIGURACOES_READ_PERMISSION]), {}, dependencies(selected, incomplete));
    await expect(incompleteLoads.configuracoes).resolves.toMatchObject({ kind: "problem", problem: { status: 502, codigo: "resposta_backend_invalida" } });
    const crossWallet: FetchLike = async () => Response.json([{ ...configuracao(), carteira_id: "00000000-0000-4000-8000-000000000099" }]);
    const crossLoads = await beginConfiguracoesLoads(await cookieStore(selected), context([CONFIGURACOES_READ_PERMISSION]), {}, dependencies(selected, crossWallet));
    await expect(crossLoads.configuracoes).resolves.toMatchObject({ kind: "problem", problem: { status: 502, codigo: "resposta_backend_invalida" } });
  });

  it("mantem erros seguros e correlacionados sem vazar mensagem estruturada", async () => {
    for (const status of [400, 401, 403, 404, 409, 422, 500] as const) {
      const selected = config();
      const backend: FetchLike = async () => Response.json({ codigo: "interno", mensagem: "stack cross-carteira" }, { status, headers: { "X-Correlation-ID": "corr-safe" } });
      const loads = await beginConfiguracoesLoads(await cookieStore(selected), context([CONFIGURACOES_READ_PERMISSION]), {}, dependencies(selected, backend));
      const result = await loads.configuracoes;
      expect(result.kind).toBe("problem");
      if (result.kind === "problem") {
        expect(result.problem.correlationId).toBe("corr-safe");
        expect(result.problem.mensagem).not.toContain("cross-carteira");
      }
    }
  });

  it("executa os comandos oficiais sem inventar Idempotency-Key", async () => {
    const selected = config();
    const seen: string[] = [];
    const backend = vi.fn<FetchLike>(async (request) => {
      const url = new URL(request.url);
      seen.push(`${request.method} ${url.pathname}`);
      expect(request.headers.get("Idempotency-Key")).toBeNull();
      expect(request.headers.get("X-Correlation-ID")).toBeTruthy();
      if (url.pathname.endsWith("/modalidades")) return Response.json(modalidade(), { status: 201, headers: { "X-Correlation-ID": "corr-command" } });
      if (url.pathname.endsWith("/calendarios")) return Response.json(calendario(), { status: 201, headers: { "X-Correlation-ID": "corr-command" } });
      if (url.pathname.endsWith("/snapshots")) return Response.json(snapshot(), { headers: { "X-Correlation-ID": "corr-command" } });
      return Response.json(configuracao(), { status: url.pathname === "/credit/configuracoes-financeiras" ? 201 : 200, headers: { "X-Correlation-ID": "corr-command" } });
    });
    const cookie = await cookieStore(selected);
    const ctx = context([CONFIGURACOES_MANAGE_PERMISSION, CONFIGURACOES_APPROVE_PERMISSION, CONFIGURACOES_ACTIVATE_PERMISSION, MODALIDADE_MANAGE_PERMISSION, CALENDARIO_MANAGE_PERMISSION, SNAPSHOT_CAPTURE_PERMISSION]);
    await expect(createModalidade(cookie, ctx, form({ modalidade_codigo: "consignado", modalidade_nome: "Consignado" }), dependencies(selected, backend))).resolves.toMatchObject({ kind: "success" });
    await expect(createCalendario(cookie, ctx, form({ calendario_codigo: "br", calendario_nome: "Brasil", feriados: "2026-01-01" }), dependencies(selected, backend))).resolves.toMatchObject({ kind: "success" });
    await expect(createConfiguracao(cookie, ctx, form({ config_modalidade: "consignado", config_calendario_id: CALENDAR_ID, vigencia_inicio: "2026-08-14", taxas_json: '[{"nome":"taxa","valor":"0.00","periodicidade":"mensal"}]', parametros_json: '[{"nome":"limite","valor":"opaco"}]', politica_json: '{"modo":"meio_para_cima","escala":2}' }), dependencies(selected, backend))).resolves.toMatchObject({ kind: "success" });
    await expect(approveConfiguracao(cookie, ctx, form({ configuracao_id: CONFIG_ID, motivo: "governado" }), dependencies(selected, backend))).resolves.toMatchObject({ kind: "success" });
    await expect(programConfiguracao(cookie, ctx, form({ configuracao_id: CONFIG_ID, data_ativacao: "2026-08-20" }), dependencies(selected, backend))).resolves.toMatchObject({ kind: "success" });
    await expect(activateConfiguracao(cookie, ctx, form({ configuracao_id: CONFIG_ID }), dependencies(selected, backend))).resolves.toMatchObject({ kind: "success" });
    await expect(inactivateConfiguracao(cookie, ctx, form({ configuracao_id: CONFIG_ID }), dependencies(selected, backend))).resolves.toMatchObject({ kind: "success" });
    await expect(captureSnapshot(cookie, ctx, form({ configuracao_id: CONFIG_ID, motivo: "evidencia" }), dependencies(selected, backend))).resolves.toMatchObject({ kind: "success" });
    expect(seen.sort()).toEqual([
      "POST /credit/configuracoes-financeiras",
      "POST /credit/configuracoes-financeiras/calendarios",
      "POST /credit/configuracoes-financeiras/modalidades",
      "POST /credit/configuracoes-financeiras/snapshots",
      `POST /credit/configuracoes-financeiras/${CONFIG_ID}/aprovar`,
      `POST /credit/configuracoes-financeiras/${CONFIG_ID}/ativar`,
      `POST /credit/configuracoes-financeiras/${CONFIG_ID}/inativar`,
      `POST /credit/configuracoes-financeiras/${CONFIG_ID}/programar`,
    ].sort());
  });
});
