import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { AgendaComunicacaoPage, AgendaLoadingState } from "../../src/components/agenda/agenda-comunicacao";
import type { AgendaActionState, AgendaResponse, CommunicationHistory } from "../../src/lib/agenda/agenda-policy";

const action = vi.fn(async (): Promise<AgendaActionState> => ({ correlationId: "corr-action", kind: "success", message: "Comunicacao idempotente registrada.", status: 200 }));

const agendaData: AgendaResponse = {
  compromissos: [{
    agenda_item_id: "00000000-0000-4000-8000-000000000080",
    atualizado_em: null,
    carteira_id: "00000000-0000-4000-8000-000000000003",
    devedor_id: "00000000-0000-4000-8000-000000000010",
    emprestimo_id: null,
    estado: "aberto",
    previsto_para: "2026-08-14T15:00:00Z",
    tenant_id: "00000000-0000-4000-8000-000000000001",
    titulo: "Retorno combinado",
    usuario_solicitante_id: "00000000-0000-4000-8000-000000000002",
  }],
  lembretes: [{
    agenda_item_id: "00000000-0000-4000-8000-000000000080",
    carteira_id: "00000000-0000-4000-8000-000000000003",
    enviado_por_usuario_id: "00000000-0000-4000-8000-000000000002",
    estado: "programa",
    horario: "2026-08-14T14:30:00Z",
    lembrete_id: "00000000-0000-4000-8000-000000000081",
    mensagem: "Ligar antes do retorno",
    tenant_id: "00000000-0000-4000-8000-000000000001",
  }],
  total: 2,
};

const historyData: CommunicationHistory = {
  registros: [{
    agenda_item_id: "00000000-0000-4000-8000-000000000080",
    canal: "telefone",
    carteira_id: "00000000-0000-4000-8000-000000000003",
    cobranca_acao_id: null,
    devedor_id: "00000000-0000-4000-8000-000000000010",
    emprestimo_id: null,
    ocorrido_em: "2026-08-14T16:00:00Z",
    registro_id: "00000000-0000-4000-8000-000000000082",
    responsavel_id: "00000000-0000-4000-8000-000000000002",
    resultado: "Retorno agendado",
    resumo: "Contato realizado",
    tenant_id: "00000000-0000-4000-8000-000000000001",
  }],
  total: 1,
};

function renderPage(permissions = ["agenda.ler", "agenda.compromisso.gerir", "agenda.lembrete.gerir", "notificacao.conciliar", "comunicacao.registrar", "comunicacao.ler"]) {
  render(
    <AgendaComunicacaoPage
      action={action}
      actionState={{ kind: "idle", message: "Aguardando acao." }}
      agenda={{ data: agendaData, kind: "ready" }}
      agendaFilters={{ incluirLembretes: true }}
      comunicacoes={{ data: historyData, kind: "ready" }}
      communicationFilters={{}}
      permissions={permissions}
      recoveryHref="/session/recover"
    />,
  );
}

describe("AgendaComunicacaoPage", () => {
  it("renderiza loading, listas oficiais e overflow por role/name", () => {
    render(<AgendaLoadingState />);
    expect(screen.getByRole("status", { name: /loading Agenda/i })).toBeInTheDocument();
    cleanup();
    renderPage();
    expect(screen.getByRole("heading", { level: 1, name: "Agenda e Comunicacao" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Agenda operacional" })).toHaveAttribute("data-state", "overflow");
    expect(screen.getByText("Historico de comunicacao")).toBeInTheDocument();
    expect(screen.getAllByText("Retorno combinado")).not.toHaveLength(0);
  });

  it("executa user-event em formulario e preserva textos de estados", async () => {
    renderPage();
    const user = userEvent.setup();
    await user.clear(screen.getByLabelText("Resumo"));
    await user.type(screen.getByLabelText("Resumo"), "Contato pelo telefone");
    expect(screen.getByLabelText("Resumo")).toHaveValue("Contato pelo telefone");
    expect(screen.getAllByText(/Novo compromisso/i)).not.toHaveLength(0);
    expect(screen.getAllByText(/Novo lembrete/i)).not.toHaveLength(0);
    expect(screen.getAllByText(/Registrar comunicacao/i)).not.toHaveLength(0);
  });

  it("mostra denied e 404 neutro sem vazar detalhe cross-carteira", () => {
    render(
      <AgendaComunicacaoPage
        action={action}
        actionState={{ kind: "idle", message: "Aguardando acao." }}
        agenda={{ kind: "denied" }}
        agendaFilters={{ incluirLembretes: true }}
        comunicacoes={{ kind: "problem", problem: { codigo: "recurso_indisponivel", correlationId: "corr-404", mensagem: "stack cross-carteira", status: 404 } }}
        communicationFilters={{}}
        permissions={[]}
        recoveryHref="/session/recover"
      />,
    );
    expect(screen.getAllByText("Sem permissao")).not.toHaveLength(0);
    expect(screen.getAllByText(/Agenda ou comunicacao nao encontrada ou indisponivel/i)).not.toHaveLength(0);
    expect(screen.queryByText(/stack cross-carteira/)).not.toBeInTheDocument();
  });
});
