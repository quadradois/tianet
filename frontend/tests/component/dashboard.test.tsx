import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import {
  AgendaView,
  CollectionView,
  DashboardLoadingState,
  DueDatesView,
  InvalidPeriodState,
  SummaryView,
} from "../../src/components/dashboard/dashboard";

describe("Dashboard operacional", () => {
  it("apresenta valores oficiais sem derivar indicador", () => {
    render(<SummaryView data={{
      carteira_id: "wallet-1", data_referencia: "2026-08-13", operacoes_ativas: 3,
      operacoes_quitadas: 5, acertos_pendentes: 1,
      tenant_id: "tenant-1", total_operacoes: 8, principal_a_receber: "9007199254740993.01",
      total_realizado: "123.45",
    }} />);
    expect(screen.getByText("9007199254740993.01")).toBeInTheDocument();
    expect(screen.getByText("123.45")).toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(/percentual|diferenca|projecao/i);
  });

  it("mantem situacao e valores de vencimento retornados pelo backend", async () => {
    render(<DueDatesView data={{ carteira_id: "wallet-1", data_referencia: "2026-08-13", tenant_id: "tenant-1", total: 1, itens: [{ acerto_em: "2026-08-13", devedor_id: "debtor-1", dia_de_acerto: 13, dias_sem_pagamento: 0, emprestimo_id: "loan-1", principal_original: "999.99", situacao: "situacao-oficial-longa" }] }} />);
    const region = screen.getByRole("region", { name: "Acertos retornados" });
    expect(region).toHaveAttribute("tabindex", "0");
    await userEvent.tab();
    expect(region).toHaveFocus();
    expect(screen.getAllByText("situacao-oficial-longa")).toHaveLength(2);
  });

  it("distingue empty de loading e periodo invalido", () => {
    const { rerender } = render(<DueDatesView data={{ carteira_id: "wallet-1", data_referencia: "2026-08-13", tenant_id: "tenant-1", total: 0, itens: [] }} />);
    expect(screen.getByRole("status")).toHaveTextContent("Nenhum acerto");
    rerender(<DashboardLoadingState title="Agenda do dia" />);
    expect(screen.getByRole("status", { name: "Carregando Agenda do dia" })).toBeInTheDocument();
    rerender(<InvalidPeriodState />);
    expect(screen.getByRole("alert")).toHaveTextContent("Periodo invalido (400)");
  });

  it("apresenta agenda e cobranca sem criar comandos", () => {
    const { rerender } = render(<AgendaView data={{ total: 2, compromissos: [{ agenda_item_id: "agenda-1", atualizado_em: null, carteira_id: "wallet-1", devedor_id: "debtor-1", emprestimo_id: null, estado: "aberto", previsto_para: "2026-08-13T12:00:00-03:00", tenant_id: "tenant-1", titulo: "Contato operacional", usuario_solicitante_id: "user-1" }], lembretes: [{ agenda_item_id: "agenda-1", carteira_id: "wallet-1", enviado_por_usuario_id: "user-1", estado: "enviado", horario: "2026-08-13T12:05:00-03:00", lembrete_id: "reminder-1", mensagem: "Lembrete oficial", tenant_id: "tenant-1" }] }} />);
    expect(screen.getByText("2", { selector: "span.tabular-nums" })).toBeInTheDocument();
    rerender(<CollectionView data={{ total: 1, items: [{ carteira_id: "wallet-1", caso_id: "case-1", criado_em: "2026-08-13T10:00:00Z", devedor_id: "debtor-1", emprestimo_id: null, estado: "pendente", origem: "manual", tenant_id: "tenant-1", titulo: "Caso com titulo muito longo para exercitar quebra responsiva sem perder conteudo", total_pendente: "77.70" }] }} />);
    expect(screen.getByRole("region", { name: "Fila de cobranca" })).toHaveAttribute("tabindex", "0");
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });
});
