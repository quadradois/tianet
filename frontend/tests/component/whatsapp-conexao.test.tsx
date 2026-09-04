import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { WhatsAppScreen } from "../../src/components/whatsapp/whatsapp.client";
import { INITIAL_WHATSAPP_ACTION_STATE, type WhatsAppActionState, type WhatsAppConnection } from "../../src/lib/whatsapp/whatsapp-policy";

const refresh = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ refresh }), usePathname: () => "/app/whatsapp" }));

const PENDENTE: WhatsAppConnection = {
  conectado: true,
  existe: true,
  instancia_nome: "tianet_tenant-1",
  nome_exibicao: null,
  numero: null,
  pareada: false,
};

/** Conta as chamadas e devolve um QR DIFERENTE a cada vez, como o provedor. */
function acaoQueConta(intents: string[]) {
  return async (_estado: WhatsAppActionState, dados: FormData): Promise<WhatsAppActionState> => {
    intents.push(String(dados.get("intent")));
    return { kind: "success", message: "QR gerado.", correlationId: "corr-1", qrcode: `data:image/png;base64,QR${intents.length}` };
  };
}

/**
 * Clique SEM `userEvent`: com temporizadores falsos, o `user.click` fica preso
 * na propria espera interna e o teste morre por timeout antes de medir nada.
 */
async function clicar(nome: string) {
  await act(async () => {
    fireEvent.click(screen.getByRole("button", { name: nome }));
  });
}

async function avancar(ms: number) {
  await act(async () => {
    vi.advanceTimersByTime(ms);
  });
}

describe("renovacao automatica do QR", () => {
  // So os temporizadores: `queueMicrotask` falso trava as transicoes do React 19,
  // e o teste morre no clique em vez de medir a renovacao.
  beforeEach(() => { vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout", "setInterval", "clearInterval"] }); refresh.mockReset(); });
  afterEach(() => { vi.useRealTimers(); });

  it("renova sozinha a cada 20s e para depois de cinco vezes", async () => {
    const intents: string[] = [];
    render(<WhatsAppScreen action={acaoQueConta(intents)} connection={PENDENTE} initialState={INITIAL_WHATSAPP_ACTION_STATE} podeGerir />);

    await clicar("Conectar WhatsApp");
    expect(intents).toEqual(["conectar"]);
    expect(screen.getByRole("img", { name: /QR code/i })).toHaveAttribute("src", expect.stringContaining("QR1"));

    // Antes do prazo, ninguem chama nada: renovar cedo demais e trafego a toa.
    await avancar(19_000);
    expect(intents).toHaveLength(1);

    await avancar(1_000);
    expect(intents).toEqual(["conectar", "conectar"]);
    expect(screen.getByRole("img", { name: /QR code/i })).toHaveAttribute("src", expect.stringContaining("QR2"));

    // O orcamento e de cinco renovacoes; a sexta nao acontece.
    for (let volta = 0; volta < 5; volta += 1) await avancar(20_000);
    expect(intents).toHaveLength(6);
    expect(screen.getByText(/pode ter expirado/)).toBeInTheDocument();

    // E o clique do operador devolve o orcamento inteiro.
    await clicar("Gerar novo QR");
    expect(intents).toHaveLength(7);
    await avancar(20_000);
    expect(intents).toHaveLength(8);
  });

  it("nao renova quando o operador nao pode gerir", async () => {
    const intents: string[] = [];
    render(<WhatsAppScreen action={acaoQueConta(intents)} connection={PENDENTE} initialState={INITIAL_WHATSAPP_ACTION_STATE} podeGerir={false} />);
    await avancar(120_000);
    expect(intents).toHaveLength(0);
  });
});
