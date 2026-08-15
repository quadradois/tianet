import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { AutomacaoProblemState } from "../../src/components/automacao/automacao";
import { AutomacaoActions, type AutomacaoActionsProps } from "../../src/components/automacao/automacao-actions.client";

const action = async () => ({ correlationId: "corr-automacao", kind: "success" as const, message: "ok", status: 200 });
const actions: AutomacaoActionsProps = {
  activateTemplateAction: action,
  approveTemplateAction: action,
  cancelJobAction: action,
  createTemplateAction: action,
  reconcileNotificationAction: action,
  retryJobAction: action,
};

describe("Automacao UI", () => {
  it("renderiza comandos governados por role/name", async () => {
    render(<AutomacaoActions {...actions} />);
    expect(screen.getByRole("button", { name: "Cancelar job" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry job" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Criar template" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Aprovar template" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Ativar template" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Conciliar notificacao" })).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("Codigo do template"), "template-cobranca");
    expect(screen.getByLabelText("Codigo do template")).toHaveValue("template-cobranca");
    expect(document.body).not.toHaveTextContent(/accessToken|refreshToken|Bearer|Authorization/i);
  });

  it("mantem 404 neutro e correlation visivel", () => {
    render(<AutomacaoProblemState problem={{ codigo: "recurso_indisponivel", correlationId: "corr-404", mensagem: "stack interna", status: 404 }} />);
    const alert = screen.getByRole("alert");
    expect(within(alert).getAllByText(/Automacao nao encontrada ou indisponivel/).length).toBeGreaterThanOrEqual(1);
    expect(alert).toHaveTextContent("Correlation ID: corr-404");
    expect(alert).not.toHaveTextContent("stack interna");
  });

  it("mantem 403, 409, 422 e 500 correlacionados", () => {
    for (const status of [403, 409, 422, 500]) {
      render(<AutomacaoProblemState problem={{ codigo: "problema", correlationId: `corr-${status}`, mensagem: `mensagem ${status}`, status }} />);
      expect(screen.getByRole("alert")).toHaveTextContent(`Erro ${status}`);
      expect(screen.getByRole("alert")).toHaveTextContent(`Correlation ID: corr-${status}`);
      document.body.replaceChildren();
    }
  });
});
