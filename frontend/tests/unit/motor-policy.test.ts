import { describe, expect, it } from "vitest";

import {
  formDate,
  formDateTime,
  formDecimalText,
  hasAnyMotorPermission,
  hasExactPermission,
  motorReferenceDate,
  parseOpaqueJson,
  resolveLoanFilters,
  formDataDeRecebimento,
  formMoney,
} from "../../src/lib/motor/motor-policy";

describe("politica do Motor", () => {
  it("usa permissao exata e nao aceita prefixo", () => {
    expect(hasExactPermission(["motor.emprestimo.ler"], "motor.emprestimo.ler")).toBe(true);
    expect(hasExactPermission(["motor.emprestimo.*", "motor"], "motor.emprestimo.ler")).toBe(false);
    expect(hasAnyMotorPermission(["motor.pagamento.registrar"])).toBe(true);
    expect(hasAnyMotorPermission(["motor.pagamento.*"])).toBe(false);
  });

  it("limita filtros ao OpenAPI publicado e ignora Tenant/Carteira arbitrarios", () => {
    expect(resolveLoanFilters({
      carteira_id: "hostil",
      devedor_id: "00000000-0000-4000-8000-000000000010",
      estado: "ativo",
      page: "2",
      size: "50",
      tenant_id: "hostil",
    })).toEqual({ devedorId: "00000000-0000-4000-8000-000000000010", estado: "ativo", page: 2, size: 50 });
    expect(resolveLoanFilters({ devedor_id: "hostil", estado: "liquidado", page: "0", size: "1000" })).toEqual({ page: 1, size: 20 });
  });

  it("valida datas e valores como texto sem calculo local", () => {
    const form = new FormData();
    form.set("data_referencia", "2026-08-14");
    form.set("recebido_em", "2026-08-14T12:00:00Z");
    form.set("valor", "123.45");
    expect(formDate(form, "data_referencia")).toBe("2026-08-14");
    expect(formDateTime(form, "recebido_em")).toBe("2026-08-14T12:00:00Z");
    expect(formDecimalText(form, "valor")).toBe("123.45");
    form.set("data_referencia", "2026-02-31");
    expect(formDate(form, "data_referencia")).toBeUndefined();
  });

  it("mantem renegociacao opaca e rejeita tentativa de formula financeira no browser", () => {
    const form = new FormData();
    form.set("novos_parametros", "{\"origem\":\"atendimento\"}");
    expect(parseOpaqueJson(form, "novos_parametros")).toEqual({ origem: "atendimento" });
    form.set("novos_parametros", "{\"saldo_formula\":\"principal+juros\"}");
    expect(parseOpaqueJson(form, "novos_parametros")).toBeUndefined();
  });

  it("usa data de referencia governada quando a URL e invalida", () => {
    expect(motorReferenceDate("2026-08-14")).toBe("2026-08-14");
    expect(motorReferenceDate("2026-99-99")).toBe("2026-08-14");
  });
});

describe("data do pagamento", () => {
  it("aceita a data escolhida no calendario e entrega o instante do contrato", () => {
    const form = new FormData();
    form.set("recebido_em", "2026-08-19");

    // Meio-dia UTC, e nao meia-noite: em America/Sao_Paulo `00:00Z` e 21h do dia
    // anterior, e o pagamento mudaria de dia sozinho.
    expect(formDataDeRecebimento(form, "recebido_em")).toBe("2026-08-19T12:00:00Z");
  });

  it("mantem instante completo quando ja vem assim", () => {
    const form = new FormData();
    form.set("recebido_em", "2026-08-19T15:30:00Z");

    expect(formDataDeRecebimento(form, "recebido_em")).toBe("2026-08-19T15:30:00Z");
  });

  it("recusa o que nao for data nem instante, em vez de inventar um dia", () => {
    const form = new FormData();
    for (const invalido of ["19/08/2026", "2026-13-01", "ontem", ""]) {
      form.set("recebido_em", invalido);
      expect(formDataDeRecebimento(form, "recebido_em")).toBeUndefined();
    }
  });
});

describe("valor em dinheiro no formulario", () => {
  it("aceita a virgula decimal, que e como se escreve dinheiro em portugues", () => {
    const form = new FormData();
    form.set("valor", "500,00");

    expect(formMoney(form, "valor")).toBe("500.00");
  });

  it("continua aceitando ponto e recusando o que nao for valor", () => {
    const form = new FormData();
    form.set("valor", "500.00");
    expect(formMoney(form, "valor")).toBe("500.00");
    for (const invalido of ["", "abc", "1.234,56", "-10"]) {
      form.set("valor", invalido);
      expect(formMoney(form, "valor")).toBeUndefined();
    }
  });
});
