import { describe, expect, it } from "vitest";

import {
  hasAnyAutomacaoPermission,
  hasExactAutomacaoPermission,
  JOB_READ_PERMISSION,
  NOTIFICATION_RECONCILE_PERMISSION,
  resolveAutomacaoFilters,
} from "../../src/lib/automacao/automacao-policy";

const UUID = "00000000-0000-4000-8000-000000000001";

describe("politica de Automacao", () => {
  it("usa igualdade exata sem prefixo ou wildcard", () => {
    expect(hasExactAutomacaoPermission([JOB_READ_PERMISSION], JOB_READ_PERMISSION)).toBe(true);
    expect(hasExactAutomacaoPermission(["automacao.job.*"], JOB_READ_PERMISSION)).toBe(false);
    expect(hasAnyAutomacaoPermission([NOTIFICATION_RECONCILE_PERMISSION])).toBe(true);
    expect(hasAnyAutomacaoPermission(["notificacao.*"])).toBe(false);
  });

  it("normaliza filtros sem aceitar IDs arbitrarios", () => {
    expect(resolveAutomacaoFilters({ job_id: UUID, notification_id: "hostil", size: "200", page: "2" })).toEqual({
      jobId: UUID,
      notificationId: null,
      page: 2,
      size: 20,
    });
  });

  it("mantem parametros opacos e nao calcula financeiro", async () => {
    const source = await import("../../src/lib/automacao/automacao-policy");
    expect(Object.keys(source)).toContain("resolveAutomacaoFilters");
    expect(JSON.stringify(Object.keys(source))).not.toMatch(/juros|saldo|parcela|parseFloat|NumberFormat/i);
  });
});
