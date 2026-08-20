import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import {
  LancamentoWizard,
  type DevedorResumo,
} from "../../src/components/lancamento/lancamento-wizard.client";
import type { LancamentoActionState } from "../../src/lib/lancamento/lancamento-policy";

const LOAN_ID = "00000000-0000-4000-8000-000000000022";
const DEBTOR_ID = "00000000-0000-4000-8000-000000000010";

const inicial: LancamentoActionState = { kind: "idle", message: "Preencha os dados e confirme." };

const devedores: readonly DevedorResumo[] = [
  { id: DEBTOR_ID, nome: "Cliente Recorrente", documento: "52998224725" },
];

function acaoOk() {
  return vi.fn(async (): Promise<LancamentoActionState> => ({
    kind: "success",
    message: "Emprestimo lancado.",
    correlationId: "corr-ui",
    emprestimoId: LOAN_ID,
  }));
}

async function preencherDevedorNovo(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText("CPF"), "52998224725");
  await user.type(screen.getByLabelText("Nome"), "Cliente do Wizard");
  await user.type(screen.getByLabelText("WhatsApp"), "(11) 98888-7766");
}

async function preencherCondicoes(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText("Valor emprestado"), "6000,00");
  await user.type(screen.getByLabelText("Juros ao mes (%)"), "3");
  await user.type(screen.getByLabelText("Dia do acerto"), "10");
}

describe("LancamentoWizard", () => {
  it("nao deixa avancar enquanto o devedor estiver incompleto", async () => {
    const user = userEvent.setup();
    render(<LancamentoWizard action={acaoOk()} devedores={[]} initialState={inicial} />);

    expect(screen.getByRole("button", { name: "Continuar" })).toBeDisabled();
    await user.type(screen.getByLabelText("CPF"), "52998224725");
    await user.type(screen.getByLabelText("Nome"), "Cliente do Wizard");
    // Sem WhatsApp o comprovante nao teria destino: o passo continua travado.
    expect(screen.getByRole("button", { name: "Continuar" })).toBeDisabled();

    await user.type(screen.getByLabelText("WhatsApp"), "(11) 98888-7766");
    expect(screen.getByRole("button", { name: "Continuar" })).toBeEnabled();
  });

  it("nao deixa avancar com condicoes invalidas", async () => {
    const user = userEvent.setup();
    render(<LancamentoWizard action={acaoOk()} devedores={[]} initialState={inicial} />);
    await preencherDevedorNovo(user);
    await user.click(screen.getByRole("button", { name: "Continuar" }));

    await user.type(screen.getByLabelText("Valor emprestado"), "6000,00");
    await user.type(screen.getByLabelText("Juros ao mes (%)"), "3");
    await user.type(screen.getByLabelText("Dia do acerto"), "0");

    expect(screen.getByRole("button", { name: "Continuar" })).toBeDisabled();
  });

  it("preserva o que foi digitado ao voltar um passo", async () => {
    const user = userEvent.setup();
    render(<LancamentoWizard action={acaoOk()} devedores={[]} initialState={inicial} />);
    await preencherDevedorNovo(user);
    await user.click(screen.getByRole("button", { name: "Continuar" }));
    await preencherCondicoes(user);

    await user.click(screen.getByRole("button", { name: "Voltar" }));

    expect(screen.getByLabelText("Nome")).toHaveValue("Cliente do Wizard");
    await user.click(screen.getByRole("button", { name: "Continuar" }));
    expect(screen.getByLabelText("Valor emprestado")).toHaveValue("R$ 6.000,00");
  });

  it("mascara valor brasileiro com milhar antes da confirmacao", async () => {
    const user = userEvent.setup();
    render(<LancamentoWizard action={acaoOk()} devedores={[]} initialState={inicial} />);
    await preencherDevedorNovo(user);
    await user.click(screen.getByRole("button", { name: "Continuar" }));

    await user.type(screen.getByLabelText("Valor emprestado"), "2.000");
    await user.tab();
    await user.type(screen.getByLabelText("Juros ao mes (%)"), "3");
    await user.type(screen.getByLabelText("Dia do acerto"), "10");

    expect(screen.getByLabelText("Valor emprestado")).toHaveValue("R$ 2.000,00");
    await user.click(screen.getByRole("button", { name: "Continuar" }));
    expect(screen.getByText("R$ 2.000,00")).toBeVisible();
  });

  it("chama a acao uma unica vez e oferece o emprestimo criado", async () => {
    const user = userEvent.setup();
    const action = acaoOk();
    render(<LancamentoWizard action={action} devedores={[]} initialState={inicial} />);
    await preencherDevedorNovo(user);
    await user.click(screen.getByRole("button", { name: "Continuar" }));
    await preencherCondicoes(user);
    await user.click(screen.getByRole("button", { name: "Continuar" }));

    await user.click(screen.getByRole("button", { name: "Confirmar lancamento" }));

    expect(action).toHaveBeenCalledTimes(1);
    expect(await screen.findByRole("link", { name: "Abrir o emprestimo" })).toHaveAttribute(
      "href",
      `/app/motor/${LOAN_ID}`,
    );
  });

  it("permite reusar devedor existente sem pedir cadastro", async () => {
    const user = userEvent.setup();
    render(<LancamentoWizard action={acaoOk()} devedores={devedores} initialState={inicial} />);

    await user.selectOptions(screen.getByLabelText("Devedor ja cadastrado"), DEBTOR_ID);

    expect(screen.queryByLabelText("CPF")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Continuar" })).toBeEnabled();
  });

  it("mostra o problema com correlation ID e mantem o formulario", async () => {
    const user = userEvent.setup();
    const action = vi.fn(async (): Promise<LancamentoActionState> => ({
      kind: "problem",
      message: "Nao foi possivel concluir o lancamento.",
      correlationId: "corr-409",
      status: 409,
    }));
    render(<LancamentoWizard action={action} devedores={[]} initialState={inicial} />);
    await preencherDevedorNovo(user);
    await user.click(screen.getByRole("button", { name: "Continuar" }));
    await preencherCondicoes(user);
    await user.click(screen.getByRole("button", { name: "Continuar" }));

    await user.click(screen.getByRole("button", { name: "Confirmar lancamento" }));

    expect(await screen.findByText(/corr-409/)).toBeVisible();
    expect(screen.queryByRole("link", { name: "Abrir o emprestimo" })).not.toBeInTheDocument();
  });
});
