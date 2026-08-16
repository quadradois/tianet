import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import {
  CashFlowReportView,
  DueDatesReportView,
  PaymentsReportView,
  Relatorios,
  SummaryReportView,
} from "../../src/components/relatorios/relatorios";
import type { CashFlowReport, DueDatesReport, PaymentsReport, SummaryReport } from "../../src/lib/relatorios/relatorios-policy";

const TENANT_ID = "00000000-0000-4000-8000-000000000001";
const WALLET_ID = "00000000-0000-4000-8000-000000000003";
const LOAN_ID = "00000000-0000-4000-8000-000000000010";
const PARCEL_ID = "00000000-0000-4000-8000-000000000011";
const PAYMENT_ID = "00000000-0000-4000-8000-000000000012";

const summary: SummaryReport = { carteira_id: WALLET_ID, data_referencia: "2026-08-14", operacoes_ativas: 2, operacoes_quitadas: 1, parcelas_previstas: 4, parcelas_vencidas: 1, tenant_id: TENANT_ID, total_operacoes: 3, total_previsto: "40.00", total_realizado: "10.00" };
const dueDates: DueDatesReport = { carteira_id: WALLET_ID, data_referencia: "2026-08-14", itens: [{ emprestimo_id: LOAN_ID, estado: "vencida", numero: 1, parcela_id: PARCEL_ID, situacao: "inadimplente", valor_liquidado: "0.00", valor_previsto: "10.00", vencimento: "2026-08-10" }], tenant_id: TENANT_ID, total: 1 };
const payments: PaymentsReport = { carteira_id: WALLET_ID, fim: "2026-08-31", inicio: "2026-08-01", operacoes_quitadas: [LOAN_ID], pagamentos: [{ emprestimo_id: LOAN_ID, estado: "confirmado", pagamento_id: PAYMENT_ID, recebido_em: "2026-08-12", valor_recebido: "10.00" }], tenant_id: TENANT_ID, total_realizado: "10.00" };
const cashFlow: CashFlowReport = { carteira_id: WALLET_ID, fim: "2026-08-31", inicio: "2026-08-01", itens: [{ data: "2026-08-12", pagamento_ids: [PAYMENT_ID], parcela_ids: [PARCEL_ID], previsto: "10.00", realizado: "10.00" }], tenant_id: TENANT_ID };

describe("componentes de Relatorios", () => {
  it("renderiza os quatro relatorios oficiais sem recalcular valores", () => {
    render(<><SummaryReportView data={summary} /><DueDatesReportView data={dueDates} /><PaymentsReportView data={payments} /><CashFlowReportView data={cashFlow} /></>);
    expect(screen.getByText("40.00")).toBeVisible();
    expect(screen.getAllByText(LOAN_ID).length).toBeGreaterThan(0);
    expect(screen.getAllByText(PARCEL_ID).length).toBeGreaterThan(0);
    expect(screen.getAllByText(PAYMENT_ID).length).toBeGreaterThan(0);
    expect(screen.getByRole("region", { name: "Vencimentos oficiais" })).toBeVisible();
    expect(screen.getByRole("region", { name: "Pagamentos oficiais" })).toBeVisible();
    expect(screen.getByRole("region", { name: "Fluxo previsto e realizado" })).toBeVisible();
  });

  it("pede periodo explicito quando nao ha query governada", () => {
    render(<Relatorios periodState={{ kind: "missing" }} recoveryHref="/session/recover" />);
    expect(screen.getByText(/Defina periodo/)).toBeVisible();
    expect(screen.getByText(/Nenhuma data automatica foi inventada/)).toBeVisible();
  });

  it("mostra 400 local para periodo invalido e mantem formulario acessivel", async () => {
    const user = userEvent.setup();
    render(<Relatorios periodState={{ kind: "invalid" }} recoveryHref="/session/recover" />);
    expect(screen.getByRole("alert")).toHaveTextContent("Periodo invalido (400)");
    await user.click(screen.getByRole("button", { name: "Consultar relatorios" }));
    expect(screen.getByLabelText("Data de referencia")).toBeInvalid();
  });

  it("mostra empty e overflow com nomes acessiveis por secao", () => {
    render(<><DueDatesReportView data={{ ...dueDates, itens: [], total: 0 }} /><PaymentsReportView data={{ ...payments, operacoes_quitadas: [], pagamentos: [], total_realizado: "0.00" }} /><CashFlowReportView data={{ ...cashFlow, itens: [] }} /></>);
    expect(screen.getAllByText(/empty:/)).toHaveLength(3);
  });
});
