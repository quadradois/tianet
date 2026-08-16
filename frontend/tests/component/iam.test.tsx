import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { IamProblemState } from "../../src/components/iam/iam-admin";
import { IamActions, type IamActionsProps } from "../../src/components/iam/iam-actions.client";

const action = async () => ({ correlationId: "corr-iam", kind: "success" as const, message: "ok", status: 200 });
const actions: IamActionsProps = {
  addPermissionAction: action,
  assignPerfilAction: action,
  createPerfilAction: action,
  inactivatePerfilAction: action,
  removePerfilUsuarioAction: action,
  removePermissionAction: action,
  renamePerfilAction: action,
};

describe("IAM permitido", () => {
  it("renderiza comandos governados sem lista de Usuarios", () => {
    render(<IamActions {...actions} />);
    expect(screen.getByRole("button", { name: "Criar Perfil" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Renomear Perfil" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Inativar Perfil" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Associar permissao" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Remover permissao" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Atribuir Perfil ao Usuario" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Remover Perfil do Usuario" })).toBeInTheDocument();
    expect(screen.getAllByText(/Usuario conhecido/).length).toBeGreaterThanOrEqual(1);
    expect(document.body).not.toHaveTextContent(/credencial|refreshToken|accessToken|Bearer/i);
  });

  it("mantem 404 neutro e correlation visivel", () => {
    render(<IamProblemState problem={{ codigo: "recurso_indisponivel", correlationId: "corr-404", mensagem: "stack interna", status: 404 }} />);
    const alert = screen.getByRole("alert");
    expect(within(alert).getAllByText(/IAM nao encontrado ou indisponivel/).length).toBeGreaterThanOrEqual(1);
    expect(alert).toHaveTextContent("Correlation ID: corr-404");
    expect(alert).not.toHaveTextContent("stack interna");
  });

  it("mantem 403 correlacionado quando o backend recusa a operacao", () => {
    render(<IamProblemState problem={{ codigo: "acesso_negado", correlationId: "corr-403", mensagem: "negado", status: 403 }} />);
    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("Erro 403");
    expect(alert).toHaveTextContent("Correlation ID: corr-403");
  });

  it("mantem 500 seguro quando o backend falha", () => {
    render(<IamProblemState problem={{ codigo: "erro_tecnico", correlationId: "corr-500", mensagem: "Servico IAM temporariamente indisponivel.", status: 500 }} />);
    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("Erro 500");
    expect(alert).toHaveTextContent("Correlation ID: corr-500");
  });
});
