import { randomBytes } from "node:crypto";

import { describe, expect, it, vi } from "vitest";

import { RefreshCoordinator, type BffDependencies, type FetchLike } from "@/lib/bff/backend.server";
import { createContract, decideContract, getContract, getContractHistory, listContracts } from "@/lib/bff/contratos.server";
import type { OperationalContext } from "@/lib/bff/context.server";
import { sealSession, sessionCookieName, type BffConfig, type SessionData } from "@/lib/bff/session.server";
import type { ContractFilters } from "@/lib/contratos/contratos-policy";

const NOW = new Date("2026-08-14T12:00:00.000Z");
const TENANT_ID = "00000000-0000-4000-8000-000000000001";
const USER_ID = "00000000-0000-4000-8000-000000000002";
const WALLET_ID = "00000000-0000-4000-8000-000000000003";
const PROFILE_ID = "00000000-0000-4000-8000-000000000004";
const DEBTOR_ID = "00000000-0000-4000-8000-000000000010";
const PROPOSAL_ID = "00000000-0000-4000-8000-000000000020";
const CONTRACT_ID = "00000000-0000-4000-8000-000000000030";
const OTHER_WALLET = "00000000-0000-4000-8000-000000000099";

function config(): BffConfig {
  return { backendUrl: "http://backend.contratos.invalid", origin: "http://frontend.contratos.invalid", production: false, loginTenantIdentifier: "ACME", currentKeyId: "current", currentKey: randomBytes(32) };
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

const filters: ContractFilters = { page: 1, size: 20 };

function contract(carteira_id = WALLET_ID, estado = "rascunho") {
  return {
    assinado_em: null,
    assinado_por_usuario_id: null,
    atualizado_em: null,
    carteira_id,
    criado_em: "2026-08-14T10:00:00Z",
    criado_por_usuario_id: USER_ID,
    devedor_id: DEBTOR_ID,
    estado,
    formalizado_em: null,
    formalizado_por_usuario_id: null,
    id: CONTRACT_ID,
    liberado_em: null,
    liberado_por_usuario_id: null,
    motivo_encerramento: null,
    parametros: { produto: "assistido" },
    proposta_comercial_id: PROPOSAL_ID,
    tenant_id: TENANT_ID,
    total_eventos: 1,
  };
}

function history() {
  return [{ contrato_id: CONTRACT_ID, criado_em: "2026-08-14T10:05:00Z", estado_anterior: "rascunho", estado_posterior: "formalizado", id: "00000000-0000-4000-8000-000000000031", motivo: null, tipo: "formalizar", usuario_id: USER_ID }];
}

describe("BFF Contratos", () => {
  it("lista contratos usando somente Carteira propria e filtros oficiais", async () => {
    const selected = config();
    const seen: URL[] = [];
    const backend = vi.fn<FetchLike>(async (request) => {
      const url = new URL(request.url);
      seen.push(url);
      expect(request.headers.get("Authorization")).toBe("Bearer access-sensitive");
      expect(request.headers.has("Idempotency-Key")).toBe(false);
      return Response.json({ items: [contract()], page: 1, pages: 1, size: 20, total: 1 }, { headers: { "X-Correlation-ID": "corr-list" } });
    });
    const listed = await listContracts(await cookieStore(selected), context(["contratos.contrato.ler"]), { ...filters, devedorId: DEBTOR_ID, estado: "rascunho" }, dependencies(selected, backend));
    expect(listed.kind).toBe("ready");
    expect(seen[0]?.pathname).toBe(`/credit/carteiras/${WALLET_ID}/contratos`);
    expect(seen[0]?.searchParams.get("devedor_id")).toBe(DEBTOR_ID);
    expect(seen[0]?.searchParams.get("estado")).toBe("rascunho");
    expect(seen[0]?.searchParams.has("carteira_id")).toBe(false);
  });

  it("nao chama backend sem permissao exata", async () => {
    const selected = config();
    const backend = vi.fn<FetchLike>();
    await expect(listContracts(await cookieStore(selected), context(["contratos.contrato"]), filters, dependencies(selected, backend))).resolves.toEqual({ kind: "denied" });
    await expect(getContract(await cookieStore(selected), context([]), CONTRACT_ID, dependencies(selected, backend))).resolves.toEqual({ kind: "denied" });
    expect(backend).not.toHaveBeenCalled();
  });

  it("rejeita 200 incompleto ou de outra Carteira sem fabricar vazio", async () => {
    const selected = config();
    const missing = await getContract(await cookieStore(selected), context(["contratos.contrato.ler"]), CONTRACT_ID, dependencies(selected, async () => Response.json({ ...contract(), total_eventos: undefined })));
    expect(missing).toMatchObject({ kind: "problem", problem: { status: 502, codigo: "resposta_backend_invalida" } });
    const cross = await getContract(await cookieStore(selected), context(["contratos.contrato.ler"]), CONTRACT_ID, dependencies(selected, async () => Response.json(contract(OTHER_WALLET))));
    expect(cross).toMatchObject({ kind: "problem", problem: { status: 502, codigo: "resposta_backend_invalida" } });
  });

  it("rejeita UUIDs obrigatorios invalidos em contrato, historico e saida logica", async () => {
    const selected = config();
    const malformedContract = await getContract(await cookieStore(selected), context(["contratos.contrato.ler"]), CONTRACT_ID, dependencies(selected, async () => Response.json({ ...contract(), devedor_id: "nao-uuid" })));
    expect(malformedContract).toMatchObject({ kind: "problem", problem: { status: 502, codigo: "resposta_backend_invalida" } });

    const malformedHistory = await getContractHistory(await cookieStore(selected), context(["contratos.contrato.ler"]), CONTRACT_ID, dependencies(selected, async () => Response.json([{ ...history()[0], usuario_id: "nao-uuid" }])));
    expect(malformedHistory).toMatchObject({ kind: "problem", problem: { status: 502, codigo: "resposta_backend_invalida" } });

    const malformedRelease = await decideContract(await cookieStore(selected), context(["contratos.contrato.liberar"]), CONTRACT_ID, "liberar-para-motor", new FormData(), dependencies(selected, async () => Response.json({ contrato_id: CONTRACT_ID, proposta_comercial_id: "nao-uuid", tenant_id: TENANT_ID, carteira_id: WALLET_ID, devedor_id: DEBTOR_ID, parametros_contratados: { produto: "assistido" }, liberado_por_usuario_id: USER_ID, liberado_em: "2026-08-14T10:30:00Z" })));
    expect(malformedRelease).toMatchObject({ kind: "problem", message: "Servico temporariamente indisponivel.", status: 502 });
  });

  it("consulta detalhe e historico pelos endpoints oficiais", async () => {
    const selected = config();
    const paths: string[] = [];
    const backend: FetchLike = async (request) => {
      const url = new URL(request.url);
      paths.push(`${request.method} ${url.pathname}`);
      return Response.json(url.pathname.endsWith("/historico") ? history() : contract(), { headers: { "X-Correlation-ID": "corr-read" } });
    };
    await expect(getContract(await cookieStore(selected), context(["contratos.contrato.ler"]), CONTRACT_ID, dependencies(selected, backend))).resolves.toMatchObject({ kind: "ready" });
    await expect(getContractHistory(await cookieStore(selected), context(["contratos.contrato.ler"]), CONTRACT_ID, dependencies(selected, backend))).resolves.toMatchObject({ kind: "ready" });
    expect(paths).toEqual([`GET /credit/contratos/${CONTRACT_ID}`, `GET /credit/contratos/${CONTRACT_ID}/historico`]);
  });

  it("mapeia 400, 403, 404, 409, 422 e 5xx com correlation e 404 neutro", async () => {
    for (const [status, expected] of [[400, "payload_invalido"], [403, "acesso_negado"], [404, "recurso_indisponivel"], [409, "conflito_estado"], [422, "regra_violada"], [500, "erro_tecnico"]] as const) {
      const selected = config();
      const result = await listContracts(await cookieStore(selected), context(["contratos.contrato.ler"]), filters, dependencies(selected, async () => Response.json({ codigo: expected, mensagem: "stack cross-carteira" }, { status, headers: { "X-Correlation-ID": "corr-safe" } })));
      expect(result.kind).toBe("problem");
      if (result.kind === "problem") {
        expect(result.problem.correlationId).toBe("corr-safe");
        expect(result.problem.codigo).toBe(expected);
        expect(result.problem.mensagem).not.toContain("cross-carteira");
      }
    }
  });

  it("executa criacao, assinatura, liberacao logica, cancelamento e encerramento com Idempotency-Key", async () => {
    const selected = config();
    const paths: string[] = [];
    const backend: FetchLike = async (request) => {
      const url = new URL(request.url);
      paths.push(`${request.method} ${url.pathname}`);
      expect(request.headers.has("Idempotency-Key")).toBe(true);
      if (url.pathname.endsWith("/liberar-para-motor")) return Response.json({ contrato_id: CONTRACT_ID, proposta_comercial_id: PROPOSAL_ID, tenant_id: TENANT_ID, carteira_id: WALLET_ID, devedor_id: DEBTOR_ID, parametros_contratados: { produto: "assistido" }, liberado_por_usuario_id: USER_ID, liberado_em: "2026-08-14T10:30:00Z" });
      return Response.json(contract(WALLET_ID, "assinado"), { status: url.pathname.endsWith("/contratos") ? 201 : 200, headers: { "X-Correlation-ID": "corr-command" } });
    };
    const form = new FormData();
    form.set("proposta_comercial_id", PROPOSAL_ID);
    await expect(createContract(await cookieStore(selected), context(["contratos.contrato.criar"]), form, dependencies(selected, backend))).resolves.toMatchObject({ kind: "success" });
    for (const [decision, permission] of [["assinar", "contratos.contrato.assinar"], ["liberar-para-motor", "contratos.contrato.liberar"], ["cancelar", "contratos.contrato.encerrar"], ["encerrar", "contratos.contrato.encerrar"]] as const) {
      await expect(decideContract(await cookieStore(selected), context([permission]), CONTRACT_ID, decision, new FormData(), dependencies(selected, backend))).resolves.toMatchObject({ kind: "success" });
    }
    expect(paths).toEqual([
      `POST /credit/carteiras/${WALLET_ID}/contratos`,
      `POST /credit/contratos/${CONTRACT_ID}/assinar`,
      `POST /credit/contratos/${CONTRACT_ID}/liberar-para-motor`,
      `POST /credit/contratos/${CONTRACT_ID}/cancelar`,
      `POST /credit/contratos/${CONTRACT_ID}/encerrar`,
    ]);
  });
});
