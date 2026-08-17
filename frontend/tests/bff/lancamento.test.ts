import { randomBytes } from "node:crypto";

import { describe, expect, it, vi } from "vitest";

import { RefreshCoordinator, type BffDependencies, type FetchLike } from "@/lib/bff/backend.server";
import type { OperationalContext } from "@/lib/bff/context.server";
import { criarLancamento } from "@/lib/bff/lancamento.server";
import { LANCAMENTO_PERMISSIONS } from "@/lib/lancamento/lancamento-policy";
import { sealSession, sessionCookieName, type BffConfig, type SessionData } from "@/lib/bff/session.server";

const NOW = new Date("2026-08-17T12:00:00.000Z");
const TENANT_ID = "00000000-0000-4000-8000-000000000001";
const USER_ID = "00000000-0000-4000-8000-000000000002";
const WALLET_ID = "00000000-0000-4000-8000-000000000003";
const DEBTOR_ID = "00000000-0000-4000-8000-000000000010";
const PROPOSAL_ID = "00000000-0000-4000-8000-000000000020";
const CONTRACT_ID = "00000000-0000-4000-8000-000000000021";
const LOAN_ID = "00000000-0000-4000-8000-000000000022";

function config(): BffConfig {
  return {
    backendUrl: "http://backend.lancamento.invalid",
    origin: "http://frontend.lancamento.invalid",
    production: false,
    currentKeyId: "current",
    currentKey: randomBytes(32),
  };
}

const session: SessionData = {
  accessToken: "access-sensitive",
  accessTokenExpiresAt: "2026-08-17T12:15:00Z",
  refreshToken: "refresh-sensitive",
  refreshTokenExpiresAt: "2026-08-24T12:00:00Z",
  tenantId: TENANT_ID,
  userId: USER_ID,
};

function context(permissions: readonly string[]): OperationalContext {
  return {
    carteira_padrao: { id: WALLET_ID, nome: "Carteira" },
    perfil: permissions.length ? { id: "00000000-0000-4000-8000-000000000004", nome: "Credor" } : null,
    permissoes: permissions,
    tenant: { id: TENANT_ID, identificador_institucional: "ACME", nome: "ACME" },
    usuario: { email: "credor@example.test", id: USER_ID, nome: "Credor" },
  };
}

async function cookieStore(selected: BffConfig) {
  const values = new Map<string, string>();
  values.set(sessionCookieName(selected), await sealSession(session, selected, NOW));
  return {
    get(name: string) {
      const value = values.get(name);
      return value ? { value } : undefined;
    },
    set(name: string, value: string) {
      values.set(name, value);
    },
  };
}

function dependencies(selected: BffConfig, fetch: FetchLike): BffDependencies {
  return { config: selected, fetch, now: () => NOW, timeoutMs: 1_000, refreshCoordinator: new RefreshCoordinator() };
}

function form(overrides: Record<string, string> = {}, omit: readonly string[] = []): FormData {
  const base: Record<string, string> = {
    documento: "52998224725",
    nome: "Cliente do Wizard",
    contato_whatsapp: "(11) 98888-7766",
    valor: "6000,00",
    taxa: "3",
    parcelas: "3",
    primeiro_vencimento: "2026-09-20",
    data_referencia: "2026-08-17",
    ...overrides,
  };
  const formData = new FormData();
  for (const [chave, valor] of Object.entries(base)) {
    if (!omit.includes(chave)) formData.set(chave, valor);
  }
  return formData;
}

function respostaCriada() {
  return {
    devedor_id: DEBTOR_ID,
    proposta_id: PROPOSAL_ID,
    contrato_id: CONTRACT_ID,
    emprestimo_id: LOAN_ID,
    quantidade_parcelas: 3,
  };
}

function backendOk(captura: { request?: Request } = {}): FetchLike {
  return vi.fn(async (input, init) => {
    captura.request = new Request(input as string, init);
    return new Response(JSON.stringify(respostaCriada()), {
      status: 201,
      headers: { "content-type": "application/json", "X-Correlation-ID": "corr-backend" },
    });
  }) as unknown as FetchLike;
}

describe("BFF Lancamento", () => {
  it("envia uma unica chamada com o vocabulario do Motor e Idempotency-Key", async () => {
    const selected = config();
    const captura: { request?: Request } = {};
    const resultado = await criarLancamento(
      await cookieStore(selected),
      context([...LANCAMENTO_PERMISSIONS]),
      form(),
      dependencies(selected, backendOk(captura)),
    );

    expect(resultado.kind).toBe("success");
    expect(resultado.emprestimoId).toBe(LOAN_ID);
    expect(resultado.correlationId).toBe("corr-backend");

    const request = captura.request as Request;
    expect(request.url).toContain(`/credit/carteiras/${WALLET_ID}/lancamentos`);
    expect(request.headers.get("Idempotency-Key")).toBeTruthy();
    const corpo = await request.json();
    expect(corpo.condicoes).toEqual({
      valor_contratado: "6000.00",
      taxa_juros_mensal: "0.03",
      quantidade_parcelas: 3,
      primeiro_vencimento: "2026-09-20",
      moeda: "BRL",
    });
    expect(corpo.devedor_novo.contato_whatsapp).toBe("(11) 98888-7766");
    expect(corpo.devedor_id).toBeUndefined();
  });

  it("usa devedor existente sem enviar cadastro novo", async () => {
    const selected = config();
    const captura: { request?: Request } = {};
    await criarLancamento(
      await cookieStore(selected),
      context([...LANCAMENTO_PERMISSIONS]),
      form({ devedor_id: DEBTOR_ID }, ["documento", "nome", "contato_whatsapp"]),
      dependencies(selected, backendOk(captura)),
    );

    const corpo = await (captura.request as Request).json();
    expect(corpo.devedor_id).toBe(DEBTOR_ID);
    expect(corpo.devedor_novo).toBeUndefined();
  });

  it("recusa sem qualquer uma das quatro permissoes, sem tocar no backend", async () => {
    const selected = config();
    for (const ausente of LANCAMENTO_PERMISSIONS) {
      const fetch = vi.fn() as unknown as FetchLike;
      const resultado = await criarLancamento(
        await cookieStore(selected),
        context(LANCAMENTO_PERMISSIONS.filter((p) => p !== ausente)),
        form(),
        dependencies(selected, fetch),
      );
      expect(resultado.kind).toBe("problem");
      expect(resultado.status).toBe(403);
      expect(fetch).not.toHaveBeenCalled();
    }
  });

  it("barra entrada invalida antes de ir ao backend", async () => {
    const selected = config();
    const casos: readonly [Record<string, string>, readonly string[]][] = [
      [{ contato_whatsapp: "" }, ["contato_whatsapp"]],
      [{ parcelas: "0" }, []],
      [{ primeiro_vencimento: "20/09/2026" }, []],
    ];
    for (const [overrides, omit] of casos) {
      const fetch = vi.fn() as unknown as FetchLike;
      const resultado = await criarLancamento(
        await cookieStore(selected),
        context([...LANCAMENTO_PERMISSIONS]),
        form(overrides, omit),
        dependencies(selected, fetch),
      );
      expect(resultado.kind).toBe("problem");
      expect(resultado.status).toBe(400);
      expect(fetch).not.toHaveBeenCalled();
    }
  });

  it("nao vaza detalhe interno quando o backend recusa", async () => {
    const selected = config();
    const fetch = vi.fn(
      async () =>
        new Response(JSON.stringify({ codigo: "conflito_estado", mensagem: "stack interno" }), {
          status: 409,
          headers: { "content-type": "application/json", "X-Correlation-ID": "corr-409" },
        }),
    ) as unknown as FetchLike;

    const resultado = await criarLancamento(
      await cookieStore(selected),
      context([...LANCAMENTO_PERMISSIONS]),
      form(),
      dependencies(selected, fetch),
    );

    expect(resultado.kind).toBe("problem");
    expect(resultado.status).toBe(409);
    expect(resultado.correlationId).toBe("corr-409");
    expect(resultado.message).not.toContain("stack interno");
  });

  it("sem data_referencia no formulario, usa hoje e nunca o primeiro vencimento", async () => {
    // O wizard nao tem esse campo. O fallback anterior era o proprio vencimento,
    // o que gera periodo de duracao zero: o Motor recusa com
    // "data_fim deve ser posterior a data_inicio". Defeito encontrado apenas na
    // stack real, porque todo teste daqui mandava o campo preenchido.
    const selected = config();
    const captura: { request?: Request } = {};
    await criarLancamento(
      await cookieStore(selected),
      context([...LANCAMENTO_PERMISSIONS]),
      form({}, ["data_referencia"]),
      dependencies(selected, backendOk(captura)),
    );

    const corpo = await (captura.request as Request).json();
    expect(corpo.data_referencia).not.toBe(corpo.condicoes.primeiro_vencimento);
    expect(corpo.data_referencia < corpo.condicoes.primeiro_vencimento).toBe(true);
    expect(corpo.data_referencia).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });
});
