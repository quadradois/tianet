import { describe, expect, it } from "vitest";

import {
  CONFIGURACOES_READ_PERMISSION,
  formatOpaqueValue,
  hasExactPermission,
  resolveConfiguracoesFilters,
} from "../../src/lib/configuracoes-financeiras/configuracoes-policy";

describe("politica de Configuracoes Financeiras", () => {
  it("usa permissao exata sem prefixo ou wildcard", () => {
    expect(hasExactPermission([CONFIGURACOES_READ_PERMISSION], CONFIGURACOES_READ_PERMISSION)).toBe(true);
    expect(hasExactPermission(["configuracoes_financeiras.configuracao.*", "Configuracoes_financeiras.configuracao.ler"], CONFIGURACOES_READ_PERMISSION)).toBe(false);
  });

  it("normaliza apenas filtros contratados e datas civis reais", () => {
    expect(resolveConfiguracoesFilters({ data_referencia: "2026-08-14", estado: "ativa", modalidade: " consignado " })).toEqual({
      dataReferencia: "2026-08-14",
      estado: "ativa",
      modalidade: "consignado",
    });
    expect(resolveConfiguracoesFilters({ data_referencia: "2026-02-30", estado: "ativo" })).toEqual({});
  });

  it("preserva parametros como valor opaco sem calculo financeiro", () => {
    expect(formatOpaqueValue({ taxa: "0.0199", regra: ["opaca"] })).toBe('{"taxa":"0.0199","regra":["opaca"]}');
    expect(formatOpaqueValue("sem interpretacao")).toBe("sem interpretacao");
  });
});
