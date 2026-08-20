import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ComercialDevedorPage, ComercialLoadingState, PropostaComercialPage } from "../../src/components/comercial/comercial";
import type { ComercialActionState, ComercialProblem, Proposal, ProposalList, Simulation } from "../../src/lib/comercial/comercial-policy";

const action = vi.fn(async (): Promise<ComercialActionState> => ({ correlationId: "corr-ui", kind: "success", message: "acao concluida", status: 200 }));
const initial: ComercialActionState = { kind: "idle", message: "idle" };
const DEBTOR_ID = "00000000-0000-4000-8000-000000000010";
const PROPOSAL_ID = "00000000-0000-4000-8000-000000000020";

function proposal(overrides: Partial<Proposal> = {}): Proposal {
  return {
    aprovada_em: null,
    aprovada_por_usuario_id: null,
    atualizado_em: null,
    carteira_id: "00000000-0000-4000-8000-000000000003",
    criada_por_usuario_id: "00000000-0000-4000-8000-000000000002",
    criado_em: "2026-08-14T10:10:00Z",
    devedor_id: DEBTOR_ID,
    estado: "rascunho",
    id: PROPOSAL_ID,
    parametros: { produto: "assistido" },
    simulacao_id: "00000000-0000-4000-8000-000000000021",
    tenant_id: "00000000-0000-4000-8000-000000000001",
    total_decisoes: 0,
    ...overrides,
  };
}

function simulation(): Simulation {
  return {
    carteira_id: "00000000-0000-4000-8000-000000000003",
    criada_por_usuario_id: "00000000-0000-4000-8000-000000000002",
    criado_em: "2026-08-14T10:00:00Z",
    devedor_id: DEBTOR_ID,
    id: "00000000-0000-4000-8000-000000000021",
    parametros: { produto: "assistido" },
    tenant_id: "00000000-0000-4000-8000-000000000001",
  };
}

function list(items: Proposal[]): ProposalList {
  return { items, page: 1, pages: items.length ? 1 : 0, size: 20, total: items.length };
}

function problem(overrides: Partial<ComercialProblem>): ComercialProblem {
  return {
    codigo: "erro_tecnico",
    correlationId: "corr-ui",
    mensagem: "Servico temporariamente indisponivel.",
    status: 500,
    ...overrides,
  };
}

describe("Comercial", () => {
  it("renderiza loading, empty, filtros e formularios sem calculo", () => {
    const { rerender } = render(<ComercialLoadingState />);
    expect(screen.getByRole("status", { name: "loading Comercial" })).toBeInTheDocument();
    rerender(<ComercialDevedorPage createProposalAction={action} createSimulationAction={action} devedorId={DEBTOR_ID} filters={{ page: 1, size: 20 }} initialState={initial} permissions={["comercial.proposta.ler", "comercial.simulacao.criar", "comercial.proposta.criar"]} proposals={{ kind: "ready", data: list([]) }} recoveryHref="/session/recover" />);
    expect(screen.getByRole("heading", { name: "Simulacoes e propostas" })).toBeVisible();
    expect(screen.getByRole("status")).toHaveTextContent("Nenhuma proposta comercial encontrada para este devedor.");
    expect(screen.getByRole("button", { name: "Criar simulacao comercial" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Criar proposta comercial" })).toBeVisible();
    expect(document.body.textContent).not.toMatch(/saldo|parcela|pagamento|emprestimo|juros/i);
  });

  it("lista propostas oficiais em regiao de overflow", async () => {
    render(<ComercialDevedorPage createProposalAction={action} createSimulationAction={action} devedorId={DEBTOR_ID} filters={{ estado: "rascunho", page: 1, size: 20 }} initialState={initial} permissions={["comercial.proposta.ler"]} proposals={{ kind: "ready", data: list([proposal()]) }} recoveryHref="/session/recover" />);
    const region = screen.getByRole("region", { name: "Tabela de propostas comerciais com overflow" });
    await userEvent.tab();
    expect(region).toHaveAttribute("tabindex", "0");
    expect(screen.getByRole("link", { name: "Consultar" })).toHaveAttribute("href", `/app/comercial/propostas/${PROPOSAL_ID}`);
  });

  it("distingue denied, 404 neutro, 409 e 422 com Correlation ID", () => {
    const { rerender } = render(<ComercialDevedorPage createProposalAction={action} createSimulationAction={action} devedorId={DEBTOR_ID} filters={{ page: 1, size: 20 }} initialState={initial} permissions={[]} proposals={{ kind: "denied" }} recoveryHref="/session/recover" />);
    expect(screen.getAllByText(/denied|Sem permissao/).length).toBeGreaterThan(0);
    rerender(<ComercialDevedorPage createProposalAction={action} createSimulationAction={action} devedorId={DEBTOR_ID} filters={{ page: 1, size: 20 }} initialState={initial} permissions={["comercial.proposta.ler"]} proposals={{ kind: "problem", problem: problem({ codigo: "recurso_indisponivel", correlationId: "corr-404", mensagem: "detalhe cross", status: 404 }) }} recoveryHref="/session/recover" />);
    expect(screen.getByRole("alert")).toHaveTextContent("Recurso comercial nao encontrado ou indisponivel");
    expect(screen.getByRole("alert")).not.toHaveTextContent("cross");
    rerender(<ComercialDevedorPage createProposalAction={action} createSimulationAction={action} devedorId={DEBTOR_ID} filters={{ page: 1, size: 20 }} initialState={initial} permissions={["comercial.proposta.ler"]} proposals={{ kind: "problem", problem: problem({ codigo: "conflito_estado", correlationId: "corr-409", mensagem: "Transicao invalida (409)", status: 409 }) }} recoveryHref="/session/recover" />);
    expect(screen.getByRole("alert")).toHaveTextContent("409");
    rerender(<ComercialDevedorPage createProposalAction={action} createSimulationAction={action} devedorId={DEBTOR_ID} filters={{ page: 1, size: 20 }} initialState={initial} permissions={["comercial.proposta.ler"]} proposals={{ kind: "problem", problem: problem({ codigo: "regra_violada", correlationId: "corr-422", mensagem: "Parametro recusado (422)", status: 422 }) }} recoveryHref="/session/recover" />);
    expect(screen.getByRole("alert")).toHaveTextContent("Correlation ID: corr-422");
  });

  it("renderiza detalhe, decisoes e contrato logico sem criar etapa futura", async () => {
    const approved = proposal({ aprovada_em: "2026-08-14T11:00:00Z", aprovada_por_usuario_id: "00000000-0000-4000-8000-000000000002", estado: "aprovada", total_decisoes: 2 });
    render(<PropostaComercialPage contract={{ kind: "ready", data: { aprovada_em: "2026-08-14T11:00:00Z", aprovada_por_usuario_id: "00000000-0000-4000-8000-000000000002", carteira_id: approved.carteira_id, devedor_id: approved.devedor_id, parametros_aprovados: { produto: "assistido" }, proposta_id: approved.id, tenant_id: approved.tenant_id } }} decisionAction={action} initialState={initial} permissions={["comercial.proposta.ler", "comercial.proposta.decidir", "comercial.proposta.integrar"]} proposal={{ kind: "ready", data: approved }} recoveryHref="/session/recover" simulation={{ kind: "ready", data: simulation() }} updateAction={action} />);
    expect(screen.getByRole("heading", { name: "Proposta comercial" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "Simulacao comercial vinculada" })).toBeVisible();
    expect(screen.getByText("parametros da simulacao")).toBeVisible();
    expect(screen.getByText("contrato logico aprovado")).toBeVisible();
    expect(screen.queryByRole("link", { name: /Contrato|Motor/i })).not.toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(/saldo|parcela|pagamento|emprestimo|juros/i);
  });
});
