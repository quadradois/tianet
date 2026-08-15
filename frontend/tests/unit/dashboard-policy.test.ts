import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

import {
  businessDate,
  hasDashboardAccess,
  hasExactPermission,
  resolveDashboardPeriod,
} from "../../src/lib/dashboard/dashboard-policy";

describe("politica do Dashboard", () => {
  it("canonicaliza a data no servidor em America/Sao_Paulo", () => {
    expect(businessDate(new Date("2026-08-14T01:30:00.000Z"))).toBe("2026-08-13");
    expect(resolveDashboardPeriod(undefined, new Date("2026-08-13T12:00:00.000Z"))).toEqual({ kind: "canonical", referenceDate: "2026-08-13" });
  });

  it("aceita apenas data de calendario ISO e produz janela inclusiva explicita", () => {
    expect(resolveDashboardPeriod("2026-08-13")).toEqual({
      kind: "ready",
      period: {
        referenceDate: "2026-08-13",
        agendaStart: "2026-08-13T00:00:00.000-03:00",
        agendaEnd: "2026-08-13T23:59:59.999-03:00",
      },
    });
    for (const value of ["0100-01-01", "9999-12-31", "2026-02-30", "13/08/2026", "2026-8-13", ["2026-08-13", "2026-08-14"]]) {
      expect(resolveDashboardPeriod(value)).toEqual({ kind: "invalid" });
    }
    expect(resolveDashboardPeriod("2018-11-04")).toEqual({
      kind: "ready",
      period: {
        referenceDate: "2018-11-04",
        agendaStart: "2018-11-04T01:00:00.000-02:00",
        agendaEnd: "2018-11-04T23:59:59.999-02:00",
      },
    });
    expect(resolveDashboardPeriod("1970-01-01")).toMatchObject({ kind: "ready" });
    expect(resolveDashboardPeriod("9998-12-31")).toMatchObject({ kind: "ready" });
  });

  it("usa somente igualdade exata de permissao", () => {
    expect(hasExactPermission(["agenda.ler"], "agenda.ler")).toBe(true);
    expect(hasExactPermission(["agenda.*", "Agenda.ler", "agenda"], "agenda.ler")).toBe(false);
    expect(hasDashboardAccess([])).toBe(false);
    expect(hasDashboardAccess(["cobranca.caso.ler"])).toBe(true);
  });

  it("nao introduz agregacao ou classificacao financeira local", () => {
    const source = [
      readFileSync(resolve("src/lib/bff/dashboard.server.ts"), "utf8"),
      readFileSync(resolve("src/components/dashboard/dashboard.tsx"), "utf8"),
    ].join("\n");
    expect(source).not.toMatch(/\.reduce\s*\(|parseFloat\s*\(|parseInt\s*\(|percentual|taxa de inadimplencia|aging|juros calculado/i);
    expect(source).not.toMatch(/total_(?:previsto|realizado|pendente)\s*[+\-*/]/);
  });
});
