import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { WhatsAppScreen } from "../../src/components/whatsapp/whatsapp.client";
import { INITIAL_WHATSAPP_ACTION_STATE, type WhatsAppActionState, type WhatsAppConnection } from "../../src/lib/whatsapp/whatsapp-policy";

const refresh = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ refresh }), usePathname: () => "/app/whatsapp" }));

const PAREADA: WhatsAppConnection = {
  conectado: true,
  existe: true,
  instancia_nome: "tianet_tenant-1",
  nome_exibicao: "Barbosa",
  numero: "556299999999",
  pareada: true,
};

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

  it("com uma RENOVACAO em curso, nenhuma outra chamada parte", async () => {
    // O debounce que o provedor pediu: os mapas de client dele nao tem lock.
    //
    // A primeira versao deste teste prendia o CLIQUE — e com o estado ainda
    // `idle` o laco nem existia, entao ele passava mesmo sem o `!pendente`.
    // Prender a RENOVACAO e o unico jeito de exercitar a condicao de verdade.
    const intents: string[] = [];
    let liberar: ((estado: WhatsAppActionState) => void) | null = null;
    const acaoQuePrendeARenovacao = async (_e: WhatsAppActionState, dados: FormData): Promise<WhatsAppActionState> => {
      intents.push(String(dados.get("intent")));
      // So a SEGUNDA chamada — a renovacao — fica presa. Deixar uma promessa
      // pendurada no fim do teste contamina o proximo: a acao pendente
      // atravessa o `cleanup` e o `act` seguinte flusha no vazio.
      if (intents.length === 2) return new Promise<WhatsAppActionState>((resolve) => { liberar = resolve; });
      return { kind: "success", message: "QR gerado.", correlationId: "corr-3", operacao: "conectar", qrcode: `data:image/png;base64,QR${intents.length}` };
    };

    render(<WhatsAppScreen action={acaoQuePrendeARenovacao} connection={PENDENTE} initialState={INITIAL_WHATSAPP_ACTION_STATE} podeGerir />);
    await clicar("Conectar WhatsApp");

    // A renovacao parte aos 20s e fica presa. Dai em diante, por mais que o
    // tempo passe, nenhuma segunda chamada sai — nem por timer, nem por polling.
    await avancar(20_000);
    expect(intents).toHaveLength(2);
    await avancar(120_000);
    expect(intents).toHaveLength(2);

    await act(async () => { liberar?.({ kind: "success", message: "QR gerado.", correlationId: "corr-3", operacao: "conectar", qrcode: "data:image/png;base64,QR2" }); });

    await avancar(20_000);
    expect(intents).toHaveLength(3);
  });

  it("continua renovando mesmo quando o provedor repete o MESMO QR", async () => {
    // Este e o teste que prova o `!pendente` do laco, e ele so existe porque uma
    // mutacao mostrou que o teste anterior nao provava nada: tirar o `!pendente`
    // nao mudava resultado nenhum.
    //
    // O que o `!pendente` faz de verdade e garantir que o efeito RODE DE NOVO
    // depois de cada acao. As dependencias sao `[renovacaoAtiva, qrcode,
    // formAction]`; se o provedor devolver o mesmo codigo — legitimo, o QR vive
    // 20s e uma renovacao pode cair dentro da vida do anterior —, `qrcode` nao
    // muda, e sem a alternancia do `pendente` nenhum temporizador novo e armado:
    // o laco morre calado na primeira repeticao.
    const intents: string[] = [];
    const acaoQueRepeteOQr = async (_e: WhatsAppActionState, dados: FormData): Promise<WhatsAppActionState> => {
      intents.push(String(dados.get("intent")));
      return { kind: "success", message: "QR gerado.", correlationId: "corr-5", operacao: "conectar", qrcode: "data:image/png;base64,QRIGUAL" };
    };

    render(<WhatsAppScreen action={acaoQueRepeteOQr} connection={PENDENTE} initialState={INITIAL_WHATSAPP_ACTION_STATE} podeGerir />);
    await clicar("Conectar WhatsApp");
    for (let volta = 0; volta < 4; volta += 1) await avancar(20_000);
    expect(intents).toHaveLength(5);
  });

  it("o polling roda com o QR na tela, mas nao enquanto uma escrita corre", async () => {
    // A recomendacao do provedor (§7.1) e serializar `connect`/`logout`/`qr`;
    // `status` fica de fora. Entao o polling CONTINUA — e o que faz a tela dizer
    // "Conectado" em ate 5s depois do escaneamento — mas nenhuma volta parte com
    // uma escrita em curso.
    const intents: string[] = [];
    let liberar: ((estado: WhatsAppActionState) => void) | null = null;
    const acaoQuePrendeARenovacao = async (_e: WhatsAppActionState, dados: FormData): Promise<WhatsAppActionState> => {
      intents.push(String(dados.get("intent")));
      if (intents.length === 2) return new Promise<WhatsAppActionState>((resolve) => { liberar = resolve; });
      return { kind: "success", message: "QR gerado.", correlationId: "corr-6", operacao: "conectar", qrcode: `data:image/png;base64,QR${intents.length}` };
    };

    render(<WhatsAppScreen action={acaoQuePrendeARenovacao} connection={PENDENTE} initialState={INITIAL_WHATSAPP_ACTION_STATE} podeGerir />);
    await clicar("Conectar WhatsApp");

    // Com o QR na tela e nada em voo, o polling trabalha.
    await avancar(15_000);
    expect(refresh.mock.calls.length).toBeGreaterThan(0);

    // Aos 20s a renovacao parte e fica presa — junto com a volta de polling
    // desse mesmo instante, que ja estava agendada. Dai em diante, nenhuma nova.
    await avancar(5_000);
    expect(intents).toHaveLength(2);
    const voltasAntes = refresh.mock.calls.length;
    await avancar(60_000);
    expect(refresh.mock.calls.length).toBe(voltasAntes);

    await act(async () => { liberar?.({ kind: "success", message: "QR gerado.", correlationId: "corr-6", operacao: "conectar", qrcode: "data:image/png;base64,QR2" }); });
    await avancar(5_000);
    expect(refresh.mock.calls.length).toBeGreaterThan(voltasAntes);
  });

  it("nao renova depois de desconectar", async () => {
    // O sucesso do desconectar tambem e `kind: "success"`. Sem o `operacao`, o
    // laco renasceria logo depois do logout — o defeito que o IMP-369 fechou.
    //
    // O caminho e o de verdade: conectar -> parear (a prop muda, como faria o
    // `revalidatePath`) -> desconectar -> a instancia continua existindo, nao
    // pareada. E nesse ultimo estado que o laco nao pode voltar sozinho.
    const intents: string[] = [];
    const acaoPorIntent = async (_e: WhatsAppActionState, dados: FormData): Promise<WhatsAppActionState> => {
      const intent = String(dados.get("intent"));
      intents.push(intent);
      return intent === "desconectar"
        ? { kind: "success", message: "WhatsApp desconectado.", correlationId: "corr-4", operacao: "desconectar" }
        : { kind: "success", message: "QR gerado.", correlationId: "corr-4", operacao: "conectar", qrcode: "data:image/png;base64,QRD" };
    };

    const { rerender } = render(<WhatsAppScreen action={acaoPorIntent} connection={PENDENTE} initialState={INITIAL_WHATSAPP_ACTION_STATE} podeGerir />);
    await clicar("Conectar WhatsApp");
    expect(intents).toEqual(["conectar"]);

    rerender(<WhatsAppScreen action={acaoPorIntent} connection={PAREADA} initialState={INITIAL_WHATSAPP_ACTION_STATE} podeGerir />);
    await clicar("Desconectar");
    expect(intents).toEqual(["conectar", "desconectar"]);

    rerender(<WhatsAppScreen action={acaoPorIntent} connection={PENDENTE} initialState={INITIAL_WHATSAPP_ACTION_STATE} podeGerir />);
    await avancar(120_000);
    expect(intents).toHaveLength(2);
    expect(screen.queryByRole("img", { name: /QR code/i })).not.toBeInTheDocument();
  });

  it("nao renova quando o operador nao pode gerir", async () => {
    const intents: string[] = [];
    render(<WhatsAppScreen action={acaoQueConta(intents)} connection={PENDENTE} initialState={INITIAL_WHATSAPP_ACTION_STATE} podeGerir={false} />);
    await avancar(120_000);
    expect(intents).toHaveLength(0);
  });
});
