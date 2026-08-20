import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { DevedorDetailPage, DevedoresLoadingState, DevedoresPage } from "../../src/components/devedores/devedores";
import type { Devedor, DevedorActionState, DevedorHistory, DevedoresProblem } from "../../src/lib/devedores/devedores-policy";

const action = vi.fn(async (): Promise<DevedorActionState> => ({ correlationId: "corr-ui", kind: "success", message: "acao concluida", status: 200 }));
const initial: DevedorActionState = { kind: "idle", message: "idle" };

function devedor(overrides: Partial<Devedor> = {}): Devedor {
  return {
    atualizado_em: null,
    carteira_id: "00000000-0000-4000-8000-000000000003",
    contatos: [{ preferencial: true, tipo: "email", valor: "cliente@example.test" }],
    criado_em: "2026-08-14T10:00:00Z",
    documento: "12345678909",
    estado: "ativo",
    id: "00000000-0000-4000-8000-000000000010",
    nome: "Cliente Devedor",
    ...overrides,
  };
}

const history: DevedorHistory = {
  devedor_id: "00000000-0000-4000-8000-000000000010",
  eventos: [{ acao: "criar.sucesso", criado_em: "2026-08-14T10:00:00Z", detalhes: "cadastrado", status: "sucesso" }],
};

function problem(overrides: Partial<DevedoresProblem>): DevedoresProblem {
  return {
    codigo: "erro_tecnico",
    correlationId: "corr-ui",
    mensagem: "Servico temporariamente indisponivel.",
    status: 500,
    ...overrides,
  };
}

describe("Devedores", () => {
  it("renderiza loading, empty e overflow sem links futuros", () => {
    const { rerender } = render(<DevedoresLoadingState />);
    expect(screen.getByRole("status", { name: "loading Devedores" })).toBeInTheDocument();
    rerender(<DevedoresPage createAction={action} filters={{}} initialState={initial} permissions={["devedor.ler", "devedor.criar"]} recoveryHref="/session/recover" result={{ kind: "ready", data: { items: [], page: 1, pages: 0, size: 20, total: 0 } }} />);
    // empty: a ausencia e dita em frase, nao com rotulo de estado tecnico.
    expect(screen.getAllByRole("status").some((item) => item.textContent?.includes("Nenhum devedor cadastrado ainda"))).toBe(true);
    // A tela nao explica mais a propria arquitetura ao operador.
    expect(screen.queryByText(/backend|Tenant e Carteira|idempotente/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Contrato|Motor|Agenda|Comunicacao/i })).not.toBeInTheDocument();
  });

  it("lista Devedores oficiais e torna a tabela tabulavel por overflow", async () => {
    render(<DevedoresPage createAction={action} filters={{ nome: "Cliente" }} initialState={initial} permissions={["devedor.ler"]} recoveryHref="/session/recover" result={{ kind: "ready", data: { items: [devedor()], page: 1, pages: 1, size: 20, total: 1 } }} />);
    expect(screen.getByRole("heading", { name: "Devedores" })).toBeVisible();
    const region = screen.getByRole("region", { name: "Tabela de Devedores com overflow" });
    await userEvent.tab();
    await userEvent.tab();
    await userEvent.tab();
    expect(region).toHaveAttribute("tabindex", "0");
    expect(screen.getByRole("link", { name: "Consultar" })).toHaveAttribute("href", "/app/devedores/00000000-0000-4000-8000-000000000010");
  });

  it("distingue denied, 404 neutro, conflito 409 e validacao 422 com correlation", () => {
    const { rerender } = render(<DevedoresPage createAction={action} filters={{}} initialState={initial} permissions={[]} recoveryHref="/session/recover" result={{ kind: "denied" }} />);
    expect(screen.getAllByText(/denied|Sem permissao/).length).toBeGreaterThan(0);
    rerender(<DevedoresPage createAction={action} filters={{}} initialState={initial} permissions={["devedor.ler"]} recoveryHref="/session/recover" result={{ kind: "problem", problem: problem({ codigo: "recurso_indisponivel", correlationId: "corr-404", mensagem: "detalhe cross", status: 404 }) }} />);
    expect(screen.getByRole("alert")).toHaveTextContent("Devedor nao encontrado ou indisponivel");
    expect(screen.getByRole("alert")).not.toHaveTextContent("cross");
    rerender(<DevedoresPage createAction={action} filters={{}} initialState={initial} permissions={["devedor.ler"]} recoveryHref="/session/recover" result={{ kind: "problem", problem: problem({ codigo: "devedor_ja_existe", correlationId: "corr-409", mensagem: "Conflito cadastral (409)", status: 409 }) }} />);
    expect(screen.getByRole("alert")).toHaveTextContent("409");
    rerender(<DevedoresPage createAction={action} filters={{}} initialState={initial} permissions={["devedor.ler"]} recoveryHref="/session/recover" result={{ kind: "problem", problem: problem({ codigo: "regra_violada", correlationId: "corr-422", mensagem: "Validacao cadastral (422)", status: 422 }) }} />);
    expect(screen.getByRole("alert")).toHaveTextContent("Correlation ID: corr-422");
  });

  it("renderiza detalhe, formulario e historico sem calcular regra financeira", () => {
    render(<DevedorDetailPage devedor={{ kind: "ready", data: devedor({ nome: "Nome muito longo para validar quebra responsiva no detalhe" }) }} history={{ kind: "ready", data: history }} inactivateAction={action} initialState={initial} permissions={["devedor.ler", "devedor.atualizar", "devedor.inativar", "devedor.reativar"]} reactivateAction={action} recoveryHref="/session/recover" updateAction={action} />);
    expect(screen.getByRole("heading", { name: /Nome muito longo/ })).toBeVisible();
    expect(screen.getByRole("button", { name: "Salvar alteracoes" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Inativar" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Reativar" })).toBeVisible();
    expect(document.body.textContent).not.toMatch(/juros|saldo|parcela|proposta|simulacao|contrato/i);
  });

  it("oferece Comercial somente para Devedor ativo e permissao comercial", () => {
    render(<DevedorDetailPage devedor={{ kind: "ready", data: devedor() }} history={{ kind: "ready", data: history }} inactivateAction={action} initialState={initial} permissions={["devedor.ler", "comercial.proposta.ler"]} reactivateAction={action} recoveryHref="/session/recover" updateAction={action} />);
    expect(screen.getByRole("link", { name: "Abrir Comercial deste Devedor" })).toHaveAttribute("href", "/app/devedores/00000000-0000-4000-8000-000000000010/comercial");
  });
});
