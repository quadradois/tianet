import { describe, expect, it } from "vitest";

import {
  allowedContractDecisions,
  assertOpaqueContractParameters,
  hasExactPermission,
  resolveContractFilters,
  type Contract,
} from "../../src/lib/contratos/contratos-policy";

const baseContract: Pick<Contract, "estado"> = { estado: "rascunho" };

describe("politica de Contratos", () => {
  it("usa permissao exata e nao aceita prefixo", () => {
    expect(hasExactPermission(["contratos.contrato.ler"], "contratos.contrato.ler")).toBe(true);
    expect(hasExactPermission(["contratos.contrato.*", "contratos.contrato"], "contratos.contrato.ler")).toBe(false);
  });

  it("limita filtros ao contrato OpenAPI publicado", () => {
    expect(resolveContractFilters({ estado: "assinado", page: "2", size: "50", devedor_id: "00000000-0000-4000-8000-000000000010", periodo: "2026" })).toEqual({
      devedorId: "00000000-0000-4000-8000-000000000010",
      estado: "assinado",
      page: 2,
      size: 50,
    });
    expect(resolveContractFilters({ estado: "formalizar", page: "0", size: "1000", devedor_id: "hostil" })).toEqual({ page: 1, size: 20 });
  });

  it("deriva acoes apenas de estado e permissao contratual oficial", () => {
    expect(allowedContractDecisions(baseContract, ["contratos.contrato.assinar"])).toEqual(["assinar"]);
    expect(allowedContractDecisions({ estado: "assinado" }, ["contratos.contrato.liberar", "contratos.contrato.encerrar"])).toEqual(["liberar-para-motor", "encerrar"]);
    expect(allowedContractDecisions({ estado: "liberado_para_motor" }, ["contratos.contrato.encerrar"])).toEqual(["encerrar"]);
    expect(allowedContractDecisions({ estado: "cancelado" }, ["contratos.contrato.encerrar", "contratos.contrato.liberar"])).toEqual([]);
  });

  it("mantem parametros opacos e rejeita termos de calculo financeiro local", () => {
    expect(assertOpaqueContractParameters({ produto: "assistido", canal: "manual" })).toBe(true);
    expect(assertOpaqueContractParameters({ juros_mensal: "1.5", parcela: "12" })).toBe(false);
  });
});
