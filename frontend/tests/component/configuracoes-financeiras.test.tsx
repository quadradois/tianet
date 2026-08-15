import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ConfiguracoesActions, type ConfiguracoesActionsProps } from "../../src/components/configuracoes-financeiras/configuracoes-actions.client";
import { ConfiguracoesList, DeniedState, ProblemState, VigenteView } from "../../src/components/configuracoes-financeiras/configuracoes-financeiras";

const config = {
  aprovada_em: null,
  aprovada_por_usuario_id: null,
  atualizada_em: null,
  calendario_id: "00000000-0000-4000-8000-000000000101",
  carteira_id: "00000000-0000-4000-8000-000000000003",
  criada_em: "2026-08-14T12:00:00Z",
  criada_por_usuario_id: "00000000-0000-4000-8000-000000000002",
  estado: "rascunho" as const,
  id: "00000000-0000-4000-8000-000000000100",
  modalidade: "consignado",
  parametros: { limite: "opaco" },
  tenant_id: "00000000-0000-4000-8000-000000000001",
  total_eventos: 1,
  versao: 1,
  vigencia_fim: null,
  vigencia_inicio: "2026-08-14",
};

const action = async () => ({ correlationId: "corr-test", kind: "success" as const, message: "ok", status: 200 });
const actions: ConfiguracoesActionsProps = {
  activateAction: action,
  approveAction: action,
  captureSnapshotAction: action,
  createCalendarioAction: action,
  createConfiguracaoAction: action,
  createModalidadeAction: action,
  inactivateAction: action,
  programAction: action,
};

describe("Configuracoes Financeiras", () => {
  it("renderiza configuracoes oficiais e parametros opacos por role/name", () => {
    render(<ConfiguracoesList data={[config]} />);
    const region = screen.getByRole("region", { name: "Configuracoes oficiais" });
    expect(region).toHaveAttribute("tabindex", "0");
    expect(within(region).getByRole("table", { name: "Configuracoes Financeiras oficiais retornadas pelo backend" })).toBeInTheDocument();
    expect(screen.getByText('{"limite":"opaco"}')).toBeInTheDocument();
  });

  it("renderiza configuracao vigente sem calcular parametros financeiros", () => {
    render(
      <VigenteView
        data={{
          carteira_id: config.carteira_id,
          configuracao_id: config.id,
          consultada_em: "2026-08-14T12:00:00Z",
          modalidade: "consignado",
          parametros: { limite: "opaco" },
          tenant_id: config.tenant_id,
          versao: 1,
        }}
      />,
    );
    expect(screen.getByText("consignado")).toBeInTheDocument();
    expect(screen.getByText('{"limite":"opaco"}')).toBeInTheDocument();
  });

  it("mostra estados denied, empty e correlation sem expor token", () => {
    render(
      <>
        <ProblemState result={{ kind: "problem", problem: { codigo: "erro_tecnico", correlationId: "corr-config", mensagem: "Servico temporariamente indisponivel.", status: 500 } }} />
        <DeniedState />
        <ConfiguracoesList data={[]} />
        <VigenteView data={null} />
      </>,
    );
    expect(screen.getByText(/Correlation ID: corr-config/)).toBeInTheDocument();
    expect(screen.getAllByText(/empty:/)).toHaveLength(1);
    expect(screen.getByText(/Defina modalidade e data de referencia/)).toBeInTheDocument();
    expect(screen.getByText(/Sem permissao/)).toBeInTheDocument();
    expect(document.body).not.toHaveTextContent(/accessToken|refreshToken|Bearer/);
  });

  it("mantem overflow acessivel em listas longas", () => {
    render(
      <ConfiguracoesList
        data={Array.from({ length: 4 }, (_, index) => ({
          ...config,
          id: `00000000-0000-4000-8000-00000000010${index}`,
        }))}
      />,
    );
    const region = screen.getByRole("region", { name: "Configuracoes oficiais" });
    expect(region).toHaveAttribute("tabindex", "0");
    expect(within(region).getAllByRole("row")).toHaveLength(5);
  });

  it("renderiza formularios de comando governados sem fixture de backend", () => {
    render(<ConfiguracoesActions {...actions} />);
    expect(screen.getByRole("button", { name: "Criar modalidade" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Criar calendario" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Criar configuracao" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Aprovar" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Capturar snapshot" })).toBeInTheDocument();
  });
});
