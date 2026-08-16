import { describe, expect, it } from "vitest";

import {
  allowedProposalDecisions,
  hasAnyComercialPermission,
  hasExactPermission,
  parseOpaqueParameters,
  resolveProposalFilters,
} from "../../src/lib/comercial/comercial-policy";

describe("comercial-policy", () => {
  it("usa permissao exata, sem prefixo ou wildcard", () => {
    expect(hasExactPermission(["comercial.proposta.ler"], "comercial.proposta.ler")).toBe(true);
    expect(hasExactPermission(["comercial.proposta"], "comercial.proposta.ler")).toBe(false);
    expect(hasExactPermission(["comercial.proposta.ler.extra"], "comercial.proposta.ler")).toBe(false);
    expect(hasAnyComercialPermission(["comercial.simulacao.criar"])).toBe(true);
  });

  it("normaliza filtros contratados de proposta sem periodo inventado", () => {
    expect(resolveProposalFilters({ estado: "aprovada", page: "2", size: "50" })).toEqual({ estado: "aprovada", page: 2, size: 50 });
    expect(resolveProposalFilters({ estado: "todos", page: "0", size: "500", periodo: "2026" })).toEqual({ page: 1, size: 20 });
  });

  it("mantem parametros como objeto opaco, sem inspecionar nomes de chave (DR-002)", () => {
    expect(parseOpaqueParameters('{"produto":"assistido"}')).toEqual({ produto: "assistido" });
    // O vocabulario canonico do Motor precisa atravessar o BFF intacto: transportar
    // valor digitado pelo operador nao e calcular. Ver DR-002 secao 5.
    expect(
      parseOpaqueParameters(
        '{"valor_contratado":"6000.00","quantidade_parcelas":3,"primeiro_vencimento":"2026-09-16","taxa_juros_mensal":"0.0250","moeda":"BRL"}',
      ),
    ).toEqual({
      moeda: "BRL",
      primeiro_vencimento: "2026-09-16",
      quantidade_parcelas: 3,
      taxa_juros_mensal: "0.0250",
      valor_contratado: "6000.00",
    });
    expect(parseOpaqueParameters('[]')).toBeUndefined();
    expect(parseOpaqueParameters('{}')).toBeUndefined();
    expect(parseOpaqueParameters("nao-json")).toBeUndefined();
  });

  it("exibe acoes somente por estado retornado e permissao de decisao", () => {
    expect(allowedProposalDecisions({ estado: "rascunho" }, ["comercial.proposta.decidir"])).toEqual(["enviar-para-analise", "cancelar"]);
    expect(allowedProposalDecisions({ estado: "em_analise" }, ["comercial.proposta.decidir"])).toEqual(["aprovar", "recusar", "cancelar", "expirar"]);
    expect(allowedProposalDecisions({ estado: "aprovada" }, ["comercial.proposta.decidir"])).toEqual([]);
    expect(allowedProposalDecisions({ estado: "rascunho" }, [])).toEqual([]);
  });
});
