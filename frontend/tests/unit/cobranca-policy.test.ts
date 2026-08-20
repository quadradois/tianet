import { describe, expect, it } from "vitest";

import {
  formBoolean,
  formDate,
  formMoney,
  formOptionalUuid,
  hasAnyCobrancaPermission,
  hasExactPermission,
  resolveCollectionFilters,
} from "../../src/lib/cobranca/cobranca-policy";

describe("politica de Cobranca", () => {
  it("usa permissao exata e nao aceita prefixo", () => {
    expect(hasExactPermission(["cobranca.caso.ler"], "cobranca.caso.ler")).toBe(true);
    expect(hasExactPermission(["cobranca.caso.*", "cobranca"], "cobranca.caso.ler")).toBe(false);
    expect(hasAnyCobrancaPermission(["cobranca.promessa.registrar"])).toBe(true);
    expect(hasAnyCobrancaPermission(["cobranca.promessa.*"])).toBe(false);
  });

  it("limita filtros ao OpenAPI publicado e ignora Tenant/Carteira arbitrarios", () => {
    expect(resolveCollectionFilters({
      carteira_id: "hostil",
      devedor_id: "00000000-0000-4000-8000-000000000010",
      estado: "pendente",
      tenant_id: "hostil",
    })).toEqual({ devedorId: "00000000-0000-4000-8000-000000000010", estado: "pendente" });
    expect(resolveCollectionFilters({ devedor_id: "hostil", estado: "juridico" })).toEqual({});
  });

  it("valida datas, valores declaratorios e UUID opcional sem calculo local", () => {
    const form = new FormData();
    form.set("data_promessa", "2026-08-21");
    form.set("valor_declarado", "R$ 123,45");
    form.set("emprestimo_id", "00000000-0000-4000-8000-000000000060");
    form.set("pagamento_informado", "on");
    expect(formDate(form, "data_promessa")).toBe("2026-08-21");
    expect(formMoney(form, "valor_declarado")).toBe("123.45");
    expect(formOptionalUuid(form, "emprestimo_id")).toBe("00000000-0000-4000-8000-000000000060");
    expect(formBoolean(form, "pagamento_informado")).toBe(true);
    form.set("data_promessa", "2026-02-31");
    expect(formDate(form, "data_promessa")).toBeUndefined();
  });
});
