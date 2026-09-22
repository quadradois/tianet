import { act, fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { NumeroAvisosCard } from "../../src/components/whatsapp/numero-avisos.client";
import { INITIAL_NUMERO_AVISOS_ACTION_STATE, type NumeroAvisosActionState } from "../../src/lib/whatsapp/whatsapp-policy";

vi.mock("next/navigation", () => ({ useRouter: () => ({ refresh: vi.fn() }), usePathname: () => "/app/whatsapp" }));

function acaoQueGrava(recebidos: FormData[]) {
  return async (_estado: NumeroAvisosActionState, dados: FormData): Promise<NumeroAvisosActionState> => {
    recebidos.push(dados);
    return { kind: "success", message: "Numero salvo.", numero: "5511999998888", correlationId: "corr-1" };
  };
}

describe("numero que recebe os avisos", () => {
  it("mostra o numero atual e envia o novo com uma Idempotency-Key por tentativa", async () => {
    const recebidos: FormData[] = [];
    render(<NumeroAvisosCard action={acaoQueGrava(recebidos)} initialState={INITIAL_NUMERO_AVISOS_ACTION_STATE} numero="5562988887777" podeGerir />);

    const campo = screen.getByLabelText("Numero que recebe os avisos");
    expect(campo).toHaveValue("5562988887777");

    fireEvent.change(campo, { target: { value: "5511999998888" } });
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Salvar numero" }));
    });

    expect(recebidos).toHaveLength(1);
    expect(recebidos[0]?.get("numero")).toBe("5511999998888");
    expect(String(recebidos[0]?.get("idempotency_key"))).toMatch(/^[0-9a-f-]{36}$/);
    expect(screen.getByRole("status")).toHaveTextContent("Numero salvo.");
  });

  it("sem numero cadastrado, diz que os avisos nao saem", () => {
    render(<NumeroAvisosCard action={acaoQueGrava([])} initialState={INITIAL_NUMERO_AVISOS_ACTION_STATE} numero={null} podeGerir />);

    expect(screen.getByText(/nenhum numero cadastrado/i)).toBeInTheDocument();
  });

  it("sem permissao de gerir, mostra o numero e nenhum formulario", () => {
    render(<NumeroAvisosCard action={acaoQueGrava([])} initialState={INITIAL_NUMERO_AVISOS_ACTION_STATE} numero="5562988887777" podeGerir={false} />);

    expect(screen.getByText("5562988887777")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Salvar numero" })).not.toBeInTheDocument();
  });

  it("erro vem com Correlation ID", () => {
    const erro: NumeroAvisosActionState = { kind: "problem", message: "Informe o numero com DDI.", status: 400, correlationId: "corr-x" };
    render(<NumeroAvisosCard action={acaoQueGrava([])} initialState={erro} numero={null} podeGerir />);

    expect(screen.getByRole("alert")).toHaveTextContent("Correlation ID: corr-x");
  });
});
