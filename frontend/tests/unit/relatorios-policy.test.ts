import { describe, expect, it } from "vitest";

import { hasExactPermission, isReportDate, resolveReportsPeriod } from "../../src/lib/relatorios/relatorios-policy";

describe("politica de Relatorios", () => {
  it("usa permissao exata sem prefixo, wildcard ou variacao de caixa", () => {
    expect(hasExactPermission(["relatorios.operacionais.ler"], "relatorios.operacionais.ler")).toBe(true);
    expect(hasExactPermission(["relatorios.operacionais.*", "Relatorios.operacionais.ler"], "relatorios.operacionais.ler")).toBe(false);
  });

  it("rejeita ausencia parcial ou periodo invertido sem inventar data automatica", () => {
    expect(resolveReportsPeriod({})).toEqual({ kind: "missing" });
    expect(resolveReportsPeriod({ data_referencia: "2026-08-14" })).toEqual({ kind: "invalid" });
    expect(resolveReportsPeriod({ data_referencia: "2026-08-14", fim: "2026-08-14", inicio: "2026-08-15" })).toEqual({ kind: "invalid" });
  });

  it("aceita somente datas civis reais na faixa governada", () => {
    expect(isReportDate("1970-01-01")).toBe(true);
    expect(isReportDate("9998-12-31")).toBe(true);
    expect(isReportDate("1969-12-31")).toBe(false);
    expect(isReportDate("9999-01-01")).toBe(false);
    expect(isReportDate("2026-02-30")).toBe(false);
  });

  it("resolve o periodo explicito sem normalizar timezone ou ler relogio local", () => {
    expect(resolveReportsPeriod({ data_referencia: "2026-08-14", fim: "2026-08-31", inicio: "2026-08-01" })).toEqual({
      kind: "ready",
      period: { endDate: "2026-08-31", referenceDate: "2026-08-14", startDate: "2026-08-01" },
    });
  });
});
