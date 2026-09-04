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
    return { kind: "success", message: "QR gerado.", correlationId: "corr-1", operacao: "conectar", qrcode: `data:image/png;base64,QR${intents.length}` };
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
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout", "setInterval", "clearInterval"] });
    refresh.mockReset();
    vi.spyOn(console, "error").mockImplementation(() => {});
  });

  afterEach(() => {
    vi.useRealTimers();
    const reclamacoes = vi.mocked(console.error).mock.calls;
    // O React RECLAMA no console em vez de falhar quando uma action de
    // `useActionState` e despachada fora de uma transicao — e nesse caso o
    // `pendente` para de acompanhar a requisicao, que e o que sustenta o
    // debounce. Sem esta linha, a suite passava com seis desses erros no stderr.
    expect(reclamacoes).toEqual([]);
  });

  it("renova sozinha a cada 20s e para depois de quatro vezes", async () => {
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

    // Quatro renovacoes e o teto — cinco codigos com o do clique, um ciclo do
    // provedor. A quinta renovacao nao acontece por mais que o tempo passe.
    for (let volta = 0; volta < 4; volta += 1) await avancar(20_000);
    expect(intents).toHaveLength(5);
    expect(screen.getByText(/renovacao automatica terminou/i)).toBeInTheDocument();

    // E o clique do operador devolve o orcamento inteiro.
    await clicar("Gerar novo QR");
    expect(intents).toHaveLength(6);
    await avancar(20_000);
    expect(intents).toHaveLength(7);
  });

  it("renova mesmo quando o provedor responde sem QR", async () => {
    // Caminho NORMAL logo apos o `connect`: `200` com `qrcode_base64: null`. O
    // laco amarrado ao QR na tela nunca comecava aqui, e a tela ficava esperando
    // um clique que o operador nao tinha motivo para dar.
    const intents: string[] = [];
    const acaoSemQr = async (_e: WhatsAppActionState, dados: FormData): Promise<WhatsAppActionState> => {
      intents.push(String(dados.get("intent")));
      return { kind: "success", message: "O provedor ainda esta gerando o QR.", correlationId: "corr-2", operacao: "conectar", qrcode: null };
    };

    render(<WhatsAppScreen action={acaoSemQr} connection={PENDENTE} initialState={INITIAL_WHATSAPP_ACTION_STATE} podeGerir />);
    await clicar("Conectar WhatsApp");
    expect(screen.queryByRole("img", { name: /QR code/i })).not.toBeInTheDocument();

    await avancar(20_000);
    expect(intents).toHaveLength(2);
  });

  it("nao dispara uma segunda chamada enquanto a primeira esta em curso", async () => {
    // O debounce que o provedor pediu: os mapas de client dele nao tem lock.
    const intents: string[] = [];
    let liberar: (estado: WhatsAppActionState) => void = () => {};
    const acaoPresa = async (_e: WhatsAppActionState, dados: FormData): Promise<WhatsAppActionState> => {
      intents.push(String(dados.get("intent")));
      return new Promise<WhatsAppActionState>((resolve) => { liberar = resolve; });
    };

    render(<WhatsAppScreen action={acaoPresa} connection={PENDENTE} initialState={INITIAL_WHATSAPP_ACTION_STATE} podeGerir />);
    await clicar("Conectar WhatsApp");
    expect(intents).toHaveLength(1);
    expect(screen.getByRole("button", { name: "Gerando QR..." })).toBeDisabled();

    await avancar(60_000);
    expect(intents).toHaveLength(1);

    await act(async () => { liberar({ kind: "success", message: "QR gerado.", correlationId: "corr-3", operacao: "conectar", qrcode: "data:image/png;base64,QRX" }); });
    await avancar(20_000);
    expect(intents).toHaveLength(2);
  });

  it("nao renova depois de desconectar", async () => {
    // O sucesso do desconectar tambem e `kind: "success"`. Sem o `operacao`, o
    // laco renasceria logo depois do logout — o defeito que o IMP-369 fechou.
    const intents: string[] = [];
    const acaoDesconecta = async (_e: WhatsAppActionState, dados: FormData): Promise<WhatsAppActionState> => {
      intents.push(String(dados.get("intent")));
      return { kind: "success", message: "WhatsApp desconectado.", correlationId: "corr-4", operacao: "desconectar" };
    };

    render(<WhatsAppScreen action={acaoDesconecta} connection={PENDENTE} initialState={INITIAL_WHATSAPP_ACTION_STATE} podeGerir />);
    await clicar("Conectar WhatsApp");
    await avancar(120_000);
    expect(intents).toHaveLength(1);
  });

  it("nao renova quando o operador nao pode gerir", async () => {
    const intents: string[] = [];
    render(<WhatsAppScreen action={acaoQueConta(intents)} connection={PENDENTE} initialState={INITIAL_WHATSAPP_ACTION_STATE} podeGerir={false} />);
    await avancar(120_000);
    expect(intents).toHaveLength(0);
  });
});
