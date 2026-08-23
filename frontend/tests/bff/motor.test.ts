import { randomBytes } from "node:crypto";

import { describe, expect, it, vi } from "vitest";

import { RefreshCoordinator, type BffDependencies, type FetchLike } from "@/lib/bff/backend.server";
import {
  createLoanFromContract,
  createRenegotiation,
  executeSettlement,
  getBalance,
  getCalculationMemory,
  getLoan,
  getSettlementQuote,
  listLoans,
  registerPayment,
} from "@/lib/bff/motor.server";
import type { OperationalContext } from "@/lib/bff/context.server";
import { sealSession, sessionCookieName, type BffConfig, type SessionData } from "@/lib/bff/session.server";
import type { LoanFilters } from "@/lib/motor/motor-policy";

const NOW = new Date("2026-08-14T12:00:00.000Z");
const TENANT_ID = "00000000-0000-4000-8000-000000000001";
const USER_ID = "00000000-0000-4000-8000-000000000002";
const WALLET_ID = "00000000-0000-4000-8000-000000000003";
const PROFILE_ID = "00000000-0000-4000-8000-000000000004";
const DEBTOR_ID = "00000000-0000-4000-8000-000000000010";
const CONTRACT_ID = "00000000-0000-4000-8000-000000000030";
const LOAN_ID = "00000000-0000-4000-8000-000000000040";
const OTHER_WALLET = "00000000-0000-4000-8000-000000000099";

function config(): BffConfig {
  return { backendUrl: "http://backend.motor.invalid", origin: "http://frontend.motor.invalid", production: false, loginTenantIdentifier: "ACME", currentKeyId: "current", currentKey: randomBytes(32) };
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

const filters: LoanFilters = { page: 1, size: 20 };

function memory() {
  return { arredondamentos: [], criado_em: "2026-08-14T10:05:00Z", entradas: {}, id: "00000000-0000-4000-8000-000000000050", passos: [], periodos: [], regra: {}, resultados: {}, tipo: "saldo" };
}

function loan(carteira_id = WALLET_ID) {
  return { carteira_id, contrato_id: CONTRACT_ID, criado_em: "2026-08-14T10:00:00Z", devedor_id: DEBTOR_ID, estado: "ativo", id: LOAN_ID, moeda: "BRL", parametros_financeiros: { origem: "contrato" }, principal_original: "1000.00", tenant_id: TENANT_ID };
}


function payment() {
  return { chave_idempotencia: "payment-key", emprestimo_id: LOAN_ID, estado: "processado", id: "00000000-0000-4000-8000-000000000070", memoria: memory(), recebido_em: "2026-08-14T12:00:00Z", tenant_id: TENANT_ID, valor_amortizacao: "90.00", valor_encargos: "0.00", valor_juros: "10.00", valor_recebido: "100.00" };
}

describe("BFF Motor", () => {
  it("lista Emprestimos usando somente Carteira propria e filtros oficiais", async () => {
    const selected = config();
    const seen: URL[] = [];
    const backend = vi.fn<FetchLike>(async (request) => {
      const url = new URL(request.url);
      seen.push(url);
      expect(request.headers.get("Authorization")).toBe("Bearer access-sensitive");
      expect(request.headers.has("Idempotency-Key")).toBe(false);
      return Response.json({ items: [loan()], page: 1, pages: 1, size: 20, total: 1 }, { headers: { "X-Correlation-ID": "corr-list" } });
    });
    const listed = await listLoans(await cookieStore(selected), context(["motor.emprestimo.ler"]), { ...filters, devedorId: DEBTOR_ID, estado: "ativo" }, dependencies(selected, backend));
    expect(listed.kind).toBe("ready");
    expect(seen[0]?.pathname).toBe(`/credit/carteiras/${WALLET_ID}/emprestimos`);
    expect(seen[0]?.searchParams.get("devedor_id")).toBe(DEBTOR_ID);
    expect(seen[0]?.searchParams.has("carteira_id")).toBe(false);
  });

  it("nao chama backend sem permissao exata", async () => {
    const selected = config();
    const backend = vi.fn<FetchLike>();
    await expect(listLoans(await cookieStore(selected), context(["motor.emprestimo"]), filters, dependencies(selected, backend))).resolves.toEqual({ kind: "denied" });
    await expect(getLoan(await cookieStore(selected), context([]), LOAN_ID, dependencies(selected, backend))).resolves.toEqual({ kind: "denied" });
    expect(backend).not.toHaveBeenCalled();
  });

  it("rejeita 200 incompleto ou de outra Carteira sem fabricar vazio", async () => {
    const selected = config();
    const missing = await getLoan(await cookieStore(selected), context(["motor.emprestimo.ler"]), LOAN_ID, dependencies(selected, async () => Response.json({ ...loan(), moeda: undefined })));
    expect(missing).toMatchObject({ kind: "problem", problem: { status: 502, codigo: "resposta_backend_invalida" } });
    const cross = await getLoan(await cookieStore(selected), context(["motor.emprestimo.ler"]), LOAN_ID, dependencies(selected, async () => Response.json(loan(OTHER_WALLET))));
    expect(cross).toMatchObject({ kind: "problem", problem: { status: 502, codigo: "resposta_backend_invalida" } });
  });

  it("consulta detalhe, saldo, memoria e quitacao pelos endpoints oficiais", async () => {
    const selected = config();
    const paths: string[] = [];
    const backend: FetchLike = async (request) => {
      const url = new URL(request.url);
      paths.push(`${request.method} ${url.pathname}`);
      if (url.pathname.endsWith("/saldo")) return Response.json({ data_referencia: "2026-08-14", emprestimo_id: LOAN_ID, encargos: "0.00", juros: "10.00", memoria: memory(), principal: "1000.00", tenant_id: TENANT_ID, total: "1010.00" });
      if (url.pathname.endsWith("/memoria-calculo")) return Response.json([memory()]);
      if (url.pathname.endsWith("/quitacao")) return Response.json({ emprestimo_id: LOAN_ID, memoria: memory(), tenant_id: TENANT_ID, valor_quitacao: { componentes: {}, data_referencia: "2026-08-14", moeda: "BRL", valor_total: "1010.00" } });
      return Response.json(loan());
    };
    await expect(getLoan(await cookieStore(selected), context(["motor.emprestimo.ler"]), LOAN_ID, dependencies(selected, backend))).resolves.toMatchObject({ kind: "ready" });
    await expect(getBalance(await cookieStore(selected), context(["motor.saldo.ler"]), LOAN_ID, "2026-08-14", dependencies(selected, backend))).resolves.toMatchObject({ kind: "ready" });
    await expect(getCalculationMemory(await cookieStore(selected), context(["motor.memoria.ler"]), LOAN_ID, dependencies(selected, backend))).resolves.toMatchObject({ kind: "ready" });
    await expect(getSettlementQuote(await cookieStore(selected), context(["motor.quitacao.executar"]), LOAN_ID, "2026-08-14", dependencies(selected, backend))).resolves.toMatchObject({ kind: "ready" });
    expect(paths).toEqual([
      `GET /credit/emprestimos/${LOAN_ID}`,
      `GET /credit/emprestimos/${LOAN_ID}/saldo`,
      `GET /credit/emprestimos/${LOAN_ID}/memoria-calculo`,
      `GET /credit/emprestimos/${LOAN_ID}/quitacao`,
    ]);
  });

  it("envia Idempotency-Key somente nos quatro comandos certificados", async () => {
    const selected = config();
    const keys: Array<[string, boolean]> = [];
    const backend: FetchLike = async (request) => {
      const url = new URL(request.url);
      keys.push([url.pathname, request.headers.has("Idempotency-Key")]);
      if (url.pathname.endsWith("/pagamentos")) return Response.json(payment());
      if (url.pathname.endsWith("/quitacao")) return Response.json({ emprestimo_id: LOAN_ID, estado: "quitado", memoria_quitacao: memory(), pagamento: payment(), tenant_id: TENANT_ID });
      if (url.pathname.endsWith("/renegociacoes")) return Response.json({ emprestimo_id: LOAN_ID, memoria: memory(), novos_parametros: { origem: "atendimento" }, tenant_id: TENANT_ID });
      return Response.json(loan(), { status: 201 });
    };
    const createForm = new FormData();
    createForm.set("contrato_id", CONTRACT_ID);
    await expect(createLoanFromContract(await cookieStore(selected), context(["motor.emprestimo.criar"]), createForm, dependencies(selected, backend))).resolves.toMatchObject({ kind: "success" });
    const installmentForm = new FormData();
    installmentForm.set("data_referencia", "2026-08-14");
    const paymentForm = new FormData();
    paymentForm.set("valor", "R$ 100,00");
    paymentForm.set("recebido_em", "2026-08-14T12:00:00Z");
    await expect(registerPayment(await cookieStore(selected), context(["motor.pagamento.registrar"]), LOAN_ID, paymentForm, dependencies(selected, backend))).resolves.toMatchObject({ kind: "success" });
    const settlementForm = new FormData();
    settlementForm.set("recebido_em", "2026-08-14T12:00:00Z");
    await expect(executeSettlement(await cookieStore(selected), context(["motor.quitacao.executar"]), LOAN_ID, settlementForm, dependencies(selected, backend))).resolves.toMatchObject({ kind: "success" });
    const renegotiationForm = new FormData();
    renegotiationForm.set("renegociado_em", "2026-08-14T12:00:00Z");
    renegotiationForm.set("novos_parametros", "{\"origem\":\"atendimento\"}");
    await expect(createRenegotiation(await cookieStore(selected), context(["motor.renegociacao.criar"]), LOAN_ID, renegotiationForm, dependencies(selected, backend))).resolves.toMatchObject({ kind: "success" });
    expect(keys).toEqual([
      [`/credit/contratos/${CONTRACT_ID}/emprestimos`, true],
      [`/credit/emprestimos/${LOAN_ID}/pagamentos`, true],
      [`/credit/emprestimos/${LOAN_ID}/quitacao`, true],
      [`/credit/emprestimos/${LOAN_ID}/renegociacoes`, true],
    ]);
  });

  it("mapeia 400, 403, 404, 409, 422 e 5xx com correlation e 404 neutro", async () => {
    for (const [status, expected] of [[400, "payload_invalido"], [403, "acesso_negado"], [404, "recurso_indisponivel"], [409, "conflito_estado"], [422, "regra_violada"], [500, "erro_tecnico"]] as const) {
      const selected = config();
      const result = await listLoans(await cookieStore(selected), context(["motor.emprestimo.ler"]), filters, dependencies(selected, async () => Response.json({ codigo: expected, mensagem: "stack cross-carteira" }, { status, headers: { "X-Correlation-ID": "corr-safe" } })));
      expect(result.kind).toBe("problem");
      if (result.kind === "problem") {
        expect(result.problem.correlationId).toBe("corr-safe");
        expect(result.problem.codigo).toBe(expected);
        expect(result.problem.mensagem).not.toContain("cross-carteira");
      }
    }
  });
});
