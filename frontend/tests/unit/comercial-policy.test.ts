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

  it("mantem parametros como objeto opaco e rejeita regra financeira livre", () => {
    expect(parseOpaqueParameters('{"produto":"assistido"}')).toEqual({ produto: "assistido" });
    expect(parseOpaqueParameters('{"saldo_calculado":"1"}')).toBeUndefined();
    expect(parseOpaqueParameters('[]')).toBeUndefined();
    expect(parseOpaqueParameters('{}')).toBeUndefined();
  });

  it("exibe acoes somente por estado retornado e permissao de decisao", () => {
    expect(allowedProposalDecisions({ estado: "rascunho" }, ["comercial.proposta.decidir"])).toEqual(["enviar-para-analise", "cancelar"]);
    expect(allowedProposalDecisions({ estado: "em_analise" }, ["comercial.proposta.decidir"])).toEqual(["aprovar", "recusar", "cancelar", "expirar"]);
    expect(allowedProposalDecisions({ estado: "aprovada" }, ["comercial.proposta.decidir"])).toEqual([]);
    expect(allowedProposalDecisions({ estado: "rascunho" }, [])).toEqual([]);
  });
});
