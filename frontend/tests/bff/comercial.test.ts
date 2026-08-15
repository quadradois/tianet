import { randomBytes } from "node:crypto";

import { describe, expect, it, vi } from "vitest";

import { RefreshCoordinator, type BffDependencies, type FetchLike } from "@/lib/bff/backend.server";
import {
  createCommercialProposal,
  createCommercialSimulation,
  decideCommercialProposal,
  getApprovedProposalContract,
  getCommercialProposal,
  getCommercialSimulation,
  listCommercialProposals,
  updateCommercialProposal,
} from "@/lib/bff/comercial.server";
import type { OperationalContext } from "@/lib/bff/context.server";
import { sealSession, sessionCookieName, type BffConfig, type SessionData } from "@/lib/bff/session.server";
import type { ProposalFilters } from "@/lib/comercial/comercial-policy";

const NOW = new Date("2026-08-14T12:00:00.000Z");
const TENANT_ID = "00000000-0000-4000-8000-000000000001";
const USER_ID = "00000000-0000-4000-8000-000000000002";
const WALLET_ID = "00000000-0000-4000-8000-000000000003";
const PROFILE_ID = "00000000-0000-4000-8000-000000000004";
const DEBTOR_ID = "00000000-0000-4000-8000-000000000010";
const PROPOSAL_ID = "00000000-0000-4000-8000-000000000020";
const SIMULATION_ID = "00000000-0000-4000-8000-000000000021";
const OTHER_WALLET = "00000000-0000-4000-8000-000000000099";

function config(): BffConfig {
  return { backendUrl: "http://backend.comercial.invalid", origin: "http://frontend.comercial.invalid", production: false, currentKeyId: "current", currentKey: randomBytes(32) };
}

const session: SessionData = { accessToken: "access-sensitive", accessTokenExpiresAt: "2026-08-14T12:15:00Z", refreshToken: "refresh-sensitive", refreshTokenExpiresAt: "2026-08-21T12:00:00Z", tenantId: TENANT_ID, userId: USER_ID };

function context(permissions: readonly string[]): OperationalContext {
  return { carteira_padrao: { id: WALLET_ID, nome: "Carteira" }, perfil: permissions.length ? { id: PROFILE_ID, nome: "Operador" } : null, permissoes: permissions, tenant: { id: TENANT_ID, identificador_institucional: "ACME", nome: "ACME" }, usuario: { email: "user@example.test", id: USER_ID, nome: "Operador" } };
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

const filters: ProposalFilters = { page: 1, size: 20 };

function simulation(carteira_id = WALLET_ID) {
  return { carteira_id, criada_por_usuario_id: USER_ID, criado_em: "2026-08-14T10:00:00Z", devedor_id: DEBTOR_ID, id: SIMULATION_ID, parametros: { produto: "assistido" }, tenant_id: TENANT_ID };
}

function proposal(carteira_id = WALLET_ID, estado = "rascunho") {
  return {
    aprovada_em: null,
    aprovada_por_usuario_id: null,
    atualizado_em: null,
    carteira_id,
    criada_por_usuario_id: USER_ID,
    criado_em: "2026-08-14T10:10:00Z",
    devedor_id: DEBTOR_ID,
    estado,
    id: PROPOSAL_ID,
    parametros: { produto: "assistido" },
    simulacao_id: SIMULATION_ID,
    tenant_id: TENANT_ID,
    total_decisoes: 0,
  };
}

describe("BFF Comercial", () => {
  it("lista propostas por Devedor usando somente Carteira propria e filtros contratados", async () => {
    const selected = config();
    const seen: URL[] = [];
    const backend = vi.fn<FetchLike>(async (request) => {
      const url = new URL(request.url);
      seen.push(url);
      expect(request.headers.get("Authorization")).toBe("Bearer access-sensitive");
      expect(request.cache).toBe("no-store");
      return Response.json({ items: [proposal()], page: 1, pages: 1, size: 20, total: 1 }, { headers: { "X-Correlation-ID": "corr-list" } });
    });
    const listed = await listCommercialProposals(await cookieStore(selected), context(["comercial.proposta.ler"]), DEBTOR_ID, { ...filters, estado: "rascunho" }, dependencies(selected, backend));
    expect(listed.kind).toBe("ready");
    expect(seen[0]?.pathname).toBe(`/credit/carteiras/${WALLET_ID}/devedores/${DEBTOR_ID}/propostas-comerciais`);
    expect(seen[0]?.searchParams.get("estado")).toBe("rascunho");
    expect(seen[0]?.searchParams.has("carteira_id")).toBe(false);
  });

  it("nao chama backend sem permissao exata", async () => {
    const selected = config();
    const backend = vi.fn<FetchLike>();
    await expect(listCommercialProposals(await cookieStore(selected), context(["comercial.proposta"]), DEBTOR_ID, filters, dependencies(selected, backend))).resolves.toEqual({ kind: "denied" });
    await expect(getCommercialProposal(await cookieStore(selected), context([]), PROPOSAL_ID, dependencies(selected, backend))).resolves.toEqual({ kind: "denied" });
    await expect(getCommercialSimulation(await cookieStore(selected), context([]), SIMULATION_ID, dependencies(selected, backend))).resolves.toEqual({ kind: "denied" });
    expect(backend).not.toHaveBeenCalled();
  });

  it("rejeita 200 incompleto ou de outra Carteira sem fabricar vazio", async () => {
    const selected = config();
    const missing = await listCommercialProposals(await cookieStore(selected), context(["comercial.proposta.ler"]), DEBTOR_ID, filters, dependencies(selected, async () => Response.json({ items: [{ ...proposal(), estado: undefined }], page: 1, pages: 1, size: 20, total: 1 })));
    expect(missing).toMatchObject({ kind: "problem", problem: { status: 502, codigo: "resposta_backend_invalida" } });
    const cross = await getCommercialProposal(await cookieStore(selected), context(["comercial.proposta.ler"]), PROPOSAL_ID, dependencies(selected, async () => Response.json(proposal(OTHER_WALLET))));
    expect(cross).toMatchObject({ kind: "problem", problem: { status: 502, codigo: "resposta_backend_invalida" } });
    const crossSimulation = await getCommercialSimulation(await cookieStore(selected), context(["comercial.proposta.ler"]), SIMULATION_ID, dependencies(selected, async () => Response.json(simulation(OTHER_WALLET))));
    expect(crossSimulation).toMatchObject({ kind: "problem", problem: { status: 502, codigo: "resposta_backend_invalida" } });
    const wrongSimulation = await getCommercialSimulation(await cookieStore(selected), context(["comercial.proposta.ler"]), SIMULATION_ID, dependencies(selected, async () => Response.json({ ...simulation(), id: "00000000-0000-4000-8000-000000000022" })), DEBTOR_ID);
    expect(wrongSimulation).toMatchObject({ kind: "problem", problem: { status: 502, codigo: "resposta_backend_invalida" } });
  });

  it("consulta simulacao por ID usando endpoint oficial e leitura Comercial", async () => {
    const selected = config();
    const seen: string[] = [];
    const result = await getCommercialSimulation(await cookieStore(selected), context(["comercial.proposta.ler"]), SIMULATION_ID, dependencies(selected, async (request) => {
      const url = new URL(request.url);
      seen.push(`${request.method} ${url.pathname}`);
      return Response.json(simulation(), { headers: { "X-Correlation-ID": "corr-simulation" } });
    }));
    expect(result).toMatchObject({ kind: "ready", data: { id: SIMULATION_ID, parametros: { produto: "assistido" } } });
    expect(seen).toEqual([`GET /credit/simulacoes-comerciais/${SIMULATION_ID}`]);
  });

  it("mapeia 400, 403, 404, 409, 422 e 5xx com correlation e 404 neutro", async () => {
    for (const [status, expected] of [[400, "payload_invalido"], [403, "acesso_negado"], [404, "recurso_indisponivel"], [409, "conflito_estado"], [422, "regra_violada"], [500, "erro_tecnico"]] as const) {
      const selected = config();
      const result = await listCommercialProposals(await cookieStore(selected), context(["comercial.proposta.ler"]), DEBTOR_ID, filters, dependencies(selected, async () => Response.json({ codigo: expected, mensagem: "stack cross-carteira" }, { status, headers: { "X-Correlation-ID": "corr-safe" } })));
      expect(result.kind).toBe("problem");
      if (result.kind === "problem") {
        expect(result.problem.correlationId).toBe("corr-safe");
        expect(result.problem.codigo).toBe(expected);
        expect(result.problem.mensagem).not.toContain("cross-carteira");
      }
    }
  });

  it("executa criacao de simulacao, proposta, atualizacao e decisao pelos endpoints oficiais", async () => {
    const selected = config();
    const paths: string[] = [];
    const backend: FetchLike = async (request) => {
      const url = new URL(request.url);
      paths.push(`${request.method} ${url.pathname}`);
      if (url.pathname.endsWith("/simulacoes-comerciais")) return Response.json(simulation(), { status: 201, headers: { "X-Correlation-ID": "corr-command" } });
      if (url.pathname.endsWith("/propostas-comerciais") && request.method === "POST") return Response.json(proposal(), { status: 201, headers: { "X-Correlation-ID": "corr-command" } });
      return Response.json(proposal(WALLET_ID, "em_analise"), { headers: { "X-Correlation-ID": "corr-command" } });
    };
    const form = new FormData();
    form.set("parametros", '{"produto":"assistido"}');
    await expect(createCommercialSimulation(await cookieStore(selected), context(["comercial.simulacao.criar"]), DEBTOR_ID, form, dependencies(selected, backend))).resolves.toMatchObject({ kind: "success" });
    form.set("simulacao_id", SIMULATION_ID);
    await expect(createCommercialProposal(await cookieStore(selected), context(["comercial.proposta.criar"]), DEBTOR_ID, form, dependencies(selected, backend))).resolves.toMatchObject({ kind: "success" });
    await expect(updateCommercialProposal(await cookieStore(selected), context(["comercial.proposta.criar"]), PROPOSAL_ID, form, dependencies(selected, backend))).resolves.toMatchObject({ kind: "success" });
    await expect(decideCommercialProposal(await cookieStore(selected), context(["comercial.proposta.decidir"]), PROPOSAL_ID, "enviar-para-analise", new FormData(), dependencies(selected, backend))).resolves.toMatchObject({ kind: "success" });
    expect(paths).toEqual([
      `POST /credit/carteiras/${WALLET_ID}/devedores/${DEBTOR_ID}/simulacoes-comerciais`,
      `POST /credit/carteiras/${WALLET_ID}/devedores/${DEBTOR_ID}/propostas-comerciais`,
      `PATCH /credit/propostas-comerciais/${PROPOSAL_ID}`,
      `POST /credit/propostas-comerciais/${PROPOSAL_ID}/enviar-para-analise`,
    ]);
  });

  it("consulta contrato logico aprovado sem criar etapa futura", async () => {
    const selected = config();
    const result = await getApprovedProposalContract(await cookieStore(selected), context(["comercial.proposta.integrar"]), PROPOSAL_ID, dependencies(selected, async () => Response.json({
      aprovada_em: "2026-08-14T11:00:00Z",
      aprovada_por_usuario_id: USER_ID,
      carteira_id: WALLET_ID,
      devedor_id: DEBTOR_ID,
      parametros_aprovados: { produto: "assistido" },
      proposta_id: PROPOSAL_ID,
      tenant_id: TENANT_ID,
    })));
    expect(result).toMatchObject({ kind: "ready" });
  });
});
