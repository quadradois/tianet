import { describe, expect, it } from "vitest";

import {
  hasAnyAgendaPermission,
  hasExactPermission,
  resolveAgendaFilters,
  resolveCommunicationFilters,
} from "../../src/lib/agenda/agenda-policy";

describe("agenda-policy", () => {
  it("usa permissoes exatas sem prefixo ou wildcard", () => {
    expect(hasExactPermission(["agenda.ler"], "agenda.ler")).toBe(true);
    expect(hasExactPermission(["agenda.*", "Agenda.ler"], "agenda.ler")).toBe(false);
    expect(hasAnyAgendaPermission(["comunicacao.registrar"])).toBe(true);
    expect(hasAnyAgendaPermission(["comunicacao.*", "notificacao"])).toBe(false);
  });

  it("resolve filtros oficiais sem aceitar Tenant/Carteira do browser", () => {
    const filters = resolveAgendaFilters({
      carteira_id: "00000000-0000-4000-8000-000000000099",
      devedor_id: "00000000-0000-4000-8000-000000000010",
      estado: "aberto",
      incluir_lembretes: "false",
      janela_fim: "2026-08-14T23:59:59-03:00",
      janela_inicio: "2026-08-14T00:00:00-03:00",
      tenant_id: "00000000-0000-4000-8000-000000000001",
    });
    expect(filters).toEqual({
      devedorId: "00000000-0000-4000-8000-000000000010",
      estado: "aberto",
      incluirLembretes: false,
      janelaFim: "2026-08-14T23:59:59-03:00",
      janelaInicio: "2026-08-14T00:00:00-03:00",
    });
    expect(JSON.stringify(filters)).not.toContain("carteira_id");
  });

  it("descarta datas impossiveis e filtros nao publicados", () => {
    expect(resolveAgendaFilters({ janela_inicio: "2026-02-30T00:00:00Z", prioridade: "alta", estado: "qualquer" })).toEqual({ incluirLembretes: true });
    expect(resolveCommunicationFilters({ page: "2", devedor_id: "00000000-0000-4000-8000-000000000010" })).toEqual({ devedorId: "00000000-0000-4000-8000-000000000010" });
  });
});
