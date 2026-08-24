import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import {
  AutomacaoProblemState,
  NotificationsView,
} from "../../src/components/automacao/automacao";
import { AutomacaoActions, type AutomacaoActionsProps } from "../../src/components/automacao/automacao-actions.client";
import type { NotificationList } from "../../src/lib/automacao/automacao-policy";

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

  it("explica notificacao transacional sem renderizar lembrete vazio", () => {
    const jobId = "00000000-0000-4000-8000-000000000081";
    const reminderId = "00000000-0000-4000-8000-000000000084";
    const notifications: NotificationList = {
      items: [
        {
          carteira_id: "00000000-0000-4000-8000-000000000003",
          codigo_resultado: null,
          estado: "aceita",
          id: "00000000-0000-4000-8000-000000000082",
          job_id: jobId,
          provider_message_id: "evolution-1",
          resultado_em: "2026-08-22T12:00:00Z",
        },
        {
          carteira_id: "00000000-0000-4000-8000-000000000003",
          codigo_resultado: null,
          estado: "aceita",
          id: "00000000-0000-4000-8000-000000000083",
          job_id: jobId,
          lembrete_id: reminderId,
          provider_message_id: "resend-1",
          resultado_em: "2026-08-22T12:00:00Z",
        },
      ],
      page: 1,
      pages: 1,
      size: 20,
      total: 2,
    };

    render(<NotificationsView notifications={notifications} />);

    expect(screen.getByText(`Job: ${jobId}; sem lembrete associado`)).toBeInTheDocument();
    expect(screen.getByText(`Job: ${jobId}; lembrete: ${reminderId}`)).toBeInTheDocument();
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
