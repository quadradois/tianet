import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { ContratoDetailPage, ContratosPage } from "../../src/components/contratos/contratos";
import { INITIAL_CONTRATO_ACTION_STATE, type Contract, type ContractEvent, type ContractList } from "../../src/lib/contratos/contratos-policy";

const contract: Contract = {
  assinado_em: null,
  assinado_por_usuario_id: null,
  atualizado_em: null,
  carteira_id: "00000000-0000-4000-8000-000000000003",
  criado_em: "2026-08-14T10:00:00Z",
  criado_por_usuario_id: "00000000-0000-4000-8000-000000000002",
  devedor_id: "00000000-0000-4000-8000-000000000010",
  estado: "rascunho",
  formalizado_em: null,
  formalizado_por_usuario_id: null,
  id: "00000000-0000-4000-8000-000000000030",
  liberado_em: null,
  liberado_por_usuario_id: null,
  motivo_encerramento: null,
  parametros: { produto: "assistido", canal: "operacao" },
  proposta_comercial_id: "00000000-0000-4000-8000-000000000020",
  tenant_id: "00000000-0000-4000-8000-000000000001",
  total_eventos: 1,
};

const list: ContractList = { items: [contract], page: 1, pages: 1, size: 20, total: 1 };
const events: readonly ContractEvent[] = [{
  contrato_id: contract.id,
  criado_em: "2026-08-14T10:05:00Z",
  estado_anterior: "rascunho",
  estado_posterior: "formalizado",
  id: "00000000-0000-4000-8000-000000000031",
  motivo: null,
  tipo: "formalizar",
  usuario_id: "00000000-0000-4000-8000-000000000002",
}];

async function noop() {
  return INITIAL_CONTRATO_ACTION_STATE;
}

describe("Contratos UI", () => {
  it("renderiza lista, formulario e overflow sem expor Motor financeiro", () => {
    render(<ContratosPage
      createAction={noop}
      filters={{ page: 1, size: 20 }}
      initialProposalId={contract.proposta_comercial_id}
      initialState={INITIAL_CONTRATO_ACTION_STATE}
      permissions={["contratos.contrato.criar", "contratos.contrato.ler"]}
      recoveryHref="/session/recover"
      result={{ data: list, kind: "ready" }}
    />);
    expect(screen.getByRole("heading", { name: "Contratos de Credito" })).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Proposta aprovada" })).toHaveValue(contract.proposta_comercial_id);
    expect(screen.getByRole("region", { name: "Tabela de contratos com overflow" })).toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(/accessToken|refreshToken|Criar Emprestimo/);
  });

  it("mostra estado denied sem chamar formulario de criacao", () => {
    render(<ContratosPage
      createAction={noop}
      filters={{ page: 1, size: 20 }}
      initialState={INITIAL_CONTRATO_ACTION_STATE}
      permissions={[]}
      recoveryHref="/session/recover"
      result={{ kind: "denied" }}
    />);
    expect(screen.getAllByText("denied")).toHaveLength(2);
    expect(screen.queryByRole("button", { name: "Formalizar contrato" })).not.toBeInTheDocument();
  });

  it("mantem 404 neutro e correlation visivel", () => {
    render(<ContratosPage
      createAction={noop}
      filters={{ page: 1, size: 20 }}
      initialState={INITIAL_CONTRATO_ACTION_STATE}
      permissions={["contratos.contrato.ler"]}
      recoveryHref="/session/recover"
      result={{ kind: "problem", problem: { codigo: "recurso_indisponivel", correlationId: "corr-404", mensagem: "detalhe secreto", status: 404 } }}
    />);
    expect(screen.getByRole("alert")).toHaveTextContent("Contrato nao encontrado ou indisponivel.");
    expect(screen.getByRole("alert")).toHaveTextContent("Correlation ID: corr-404");
    expect(screen.queryByText("detalhe secreto")).not.toBeInTheDocument();
  });

  it("abre dialog de assinatura por teclado e explica liberacao logica", async () => {
    const user = userEvent.setup();
    render(<ContratoDetailPage
      action={noop}
      contract={{ data: { ...contract, estado: "assinado" }, kind: "ready" }}
      history={{ data: events, kind: "ready" }}
      initialState={INITIAL_CONTRATO_ACTION_STATE}
      permissions={["contratos.contrato.liberar", "contratos.contrato.encerrar"]}
      recoveryHref="/session/recover"
    />);
    await user.click(screen.getByRole("button", { name: "Liberar contrato para Motor" }));
    expect(screen.getByRole("dialog")).toHaveTextContent("Gera somente a saida logica para o Motor futuro");
    expect(screen.getByRole("dialog")).not.toHaveTextContent("Criar Emprestimo");
  });
});
