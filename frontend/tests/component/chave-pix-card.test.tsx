import { act, fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ChavePixCard } from "../../src/components/pagamentos/chave-pix.client";
import {
  INITIAL_CHAVE_PIX_ACTION_STATE,
  type ChavePix,
  type ChavePixActionState,
} from "../../src/lib/pagamentos/mercadopago-policy";

vi.mock("next/navigation", () => ({ useRouter: () => ({ refresh: vi.fn() }), usePathname: () => "/app/pagamentos" }));

const AUSENTE: ChavePix = { tipo: null, valor: null, favorecido: null, configurada: false };
const CONFIGURADA: ChavePix = { tipo: "telefone", valor: "5562999998888", favorecido: "Ivonete", configurada: true };

function acao(recebidos: FormData[], resposta: ChavePix) {
  return async (_estado: ChavePixActionState, dados: FormData): Promise<ChavePixActionState> => {
    recebidos.push(dados);
    return { kind: "success", message: "Chave Pix salva.", chave: resposta, correlationId: "corr-1" };
  };
}

describe("card da chave Pix", () => {
  it("diz com todas as letras quando nao ha chave, porque o agente depende dela", () => {
    render(<ChavePixCard action={acao([], AUSENTE)} chave={AUSENTE} initialState={INITIAL_CHAVE_PIX_ACTION_STATE} podeConfigurar />);

    expect(screen.getByTestId("chave-pix-estado")).toHaveTextContent(/nao oferece Pix ate cadastrar/i);
  });

  it("mostra a chave atual com tipo e favorecido", () => {
    render(<ChavePixCard action={acao([], CONFIGURADA)} chave={CONFIGURADA} initialState={INITIAL_CHAVE_PIX_ACTION_STATE} podeConfigurar />);

    const estado = screen.getByTestId("chave-pix-estado");
    expect(estado).toHaveTextContent("5562999998888");
    expect(estado).toHaveTextContent("Telefone");
    expect(estado).toHaveTextContent("Ivonete");
  });

  it("envia tipo, valor e favorecido com Idempotency-Key propria", async () => {
    const recebidos: FormData[] = [];
    render(<ChavePixCard action={acao(recebidos, CONFIGURADA)} chave={AUSENTE} initialState={INITIAL_CHAVE_PIX_ACTION_STATE} podeConfigurar />);

    fireEvent.change(screen.getByLabelText("Chave", { exact: true }), { target: { value: "5562999998888" } });
    fireEvent.change(screen.getByLabelText("Nome do favorecido"), { target: { value: "Ivonete" } });
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Salvar chave" }));
    });

    expect(recebidos).toHaveLength(1);
    expect(recebidos[0]?.get("valor")).toBe("5562999998888");
    expect(recebidos[0]?.get("favorecido")).toBe("Ivonete");
    expect(recebidos[0]?.get("idempotency_key")).toBeTruthy();
  });

  it("sem permissao mostra a chave e esconde o formulario", () => {
    render(<ChavePixCard action={acao([], CONFIGURADA)} chave={CONFIGURADA} initialState={INITIAL_CHAVE_PIX_ACTION_STATE} podeConfigurar={false} />);

    expect(screen.getByTestId("chave-pix-estado")).toBeInTheDocument();
    expect(screen.queryByLabelText("Chave", { exact: true })).toBeNull();
  });
});
