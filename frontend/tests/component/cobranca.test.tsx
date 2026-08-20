import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { CobrancaPage } from "../../src/components/cobranca/cobranca";
import { INITIAL_COBRANCA_ACTION_STATE, type CollectionQueue } from "../../src/lib/cobranca/cobranca-policy";

const CASE_ID = "00000000-0000-4000-8000-000000000090";
const action = vi.fn(async () => ({ kind: "success" as const, status: 200, message: "ok", correlationId: "corr-component" }));

function queue(): CollectionQueue {
  return {
    items: [{
      carteira_id: "00000000-0000-4000-8000-000000000003",
      caso_id: CASE_ID,
      criado_em: "2026-08-14T10:00:00Z",
      devedor_id: "00000000-0000-4000-8000-000000000010",
      emprestimo_id: "00000000-0000-4000-8000-000000000040",
      estado: "pendente",
      origem: "motor",
      tenant_id: "00000000-0000-4000-8000-000000000001",
      titulo: "Parcela vencida",
      total_pendente: "100.00",
    }],
    total: 1,
  };
}

describe("CobrancaPage", () => {
  it("renderiza fila com overflow e comandos governados", () => {
    render(
      <CobrancaPage
        actionState={INITIAL_COBRANCA_ACTION_STATE}
        appropriatePaymentAction={action}
        filters={{ estado: "pendente" }}
        permissions={["cobranca.caso.ler", "cobranca.acao.registrar", "cobranca.promessa.registrar", "cobranca.promessa.apropriar"]}
        recoveryHref="/session/recover"
        registerAction={action}
        registerPromiseAction={action}
        result={{ kind: "ready", data: queue() }}
      />,
    );
    expect(screen.getByRole("heading", { level: 1, name: "Fila de cobranca" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Casos de cobranca" })).toHaveAttribute("data-state", "overflow");
    expect(screen.getAllByText("R$ 100,00").length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText(/Promessa declaratoria/).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/Pagamento oficial apropriado/).length).toBeGreaterThanOrEqual(1);
    expect(document.body.textContent).not.toMatch(/accessToken|Bearer|Authorization/i);
  });

  it("submete acao real por user-event", async () => {
    const user = userEvent.setup();
    render(
      <CobrancaPage
        actionState={INITIAL_COBRANCA_ACTION_STATE}
        appropriatePaymentAction={action}
        filters={{}}
        permissions={["cobranca.caso.ler", "cobranca.acao.registrar"]}
        recoveryHref="/session/recover"
        registerAction={action}
        registerPromiseAction={action}
        result={{ kind: "ready", data: queue() }}
      />,
    );
    await user.click(screen.getByRole("button", { name: "Acao idempotente" }));
    expect(action).toHaveBeenCalled();
  });

  it("mascara valor de promessa em BRL", async () => {
    const user = userEvent.setup();
    render(
      <CobrancaPage
        actionState={INITIAL_COBRANCA_ACTION_STATE}
        appropriatePaymentAction={action}
        filters={{ estado: "pendente" }}
        permissions={["cobranca.caso.ler", "cobranca.promessa.registrar"]}
        recoveryHref="/session/recover"
        registerAction={action}
        registerPromiseAction={action}
        result={{ kind: "ready", data: queue() }}
      />,
    );

    await user.type(screen.getByLabelText("Valor declarado"), "2.000");
    await user.tab();

    expect(screen.getByLabelText("Valor declarado")).toHaveValue("R$ 2.000,00");
  });

  it("mostra empty, denied e 404 neutro", () => {
    const base = {
      actionState: INITIAL_COBRANCA_ACTION_STATE,
      appropriatePaymentAction: action,
      filters: {},
      permissions: [] as readonly string[],
      recoveryHref: "/session/recover",
      registerAction: action,
      registerPromiseAction: action,
    };
    const { rerender } = render(<CobrancaPage {...base} result={{ kind: "denied" }} />);
    expect(screen.getByText("denied")).toBeInTheDocument();
    rerender(<CobrancaPage {...base} permissions={["cobranca.caso.ler"]} result={{ kind: "ready", data: { items: [], total: 0 } }} />);
    expect(screen.getByText(/empty:/)).toBeInTheDocument();
    rerender(<CobrancaPage {...base} result={{ kind: "problem", problem: { codigo: "x", correlationId: "corr-404", mensagem: "detalhe hostil", status: 404 } }} />);
    expect(screen.getByRole("alert")).toHaveTextContent("Caso de cobranca nao encontrado ou indisponivel.");
    expect(screen.getByRole("alert")).toHaveTextContent("Correlation ID: corr-404");
  });
});
