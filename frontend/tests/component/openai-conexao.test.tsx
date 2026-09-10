import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { OpenAIScreen } from "../../src/components/openai/openai.client";
import { INITIAL_OPENAI_ACTION_STATE, type OpenAIActionState, type OpenAIConnection, type OpenAIState } from "../../src/lib/openai/openai-policy";

const refresh = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ refresh }) }));

function connection(state: OpenAIState): OpenAIConnection {
  return { enabled: state !== "DESABILITADO", processAvailable: state !== "INDISPONIVEL" && state !== "DESABILITADO", accountConnected: ["CONECTADO", "LIMITE_ATINGIDO"].includes(state), planType: state === "CONECTADO" ? "plus" : null, state, usageSummary: null };
}

async function click(name: string | RegExp) {
  await act(async () => { fireEvent.click(screen.getByRole("button", { name })); });
}

describe("tela OpenAI", () => {
  beforeEach(() => {
    refresh.mockReset();
    Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText: vi.fn(async () => undefined) } });
  });
  afterEach(() => vi.useRealTimers());

  it.each([
    ["DESABILITADO", "Desabilitado"], ["INDISPONIVEL", "Indisponível"], ["DESCONECTADO", "Desconectado"],
    ["AGUARDANDO_USUARIO", "Aguardando você"], ["CONECTADO", "Conectado"], ["LIMITE_ATINGIDO", "Limite atingido"],
    ["ERRO", "Erro"], ["ERRO_RESULTADO_DESCONHECIDO", "Resultado desconhecido"],
  ] as const)("representa o estado %s em texto", (state, label) => {
    render(<OpenAIScreen action={async () => INITIAL_OPENAI_ACTION_STATE} connection={connection(state)} initialState={INITIAL_OPENAI_ACTION_STATE} podeGerir />);
    expect(screen.getByText(label, { exact: true })).toBeInTheDocument();
  });

  it("mostra somente link oficial, código copiável e prazo após iniciar login", async () => {
    const action = async (): Promise<OpenAIActionState> => ({ kind: "login", message: "Login iniciado.", correlationId: "corr", challenge: { verificationUrl: "https://auth.openai.com/codex/device", userCode: "ABCD-EFGH", expiresAt: "2099-01-01T00:10:00Z" } });
    render(<OpenAIScreen action={action} connection={connection("DESCONECTADO")} initialState={INITIAL_OPENAI_ACTION_STATE} podeGerir />);
    await click("Conectar conta OpenAI");
    expect(screen.getByRole("link", { name: "Abrir login oficial da OpenAI" })).toHaveAttribute("href", "https://auth.openai.com/codex/device");
    expect(screen.getByText("ABCD-EFGH")).toBeInTheDocument();
    await click("Copiar código");
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith("ABCD-EFGH");
  });

  it("faz polling limitado apenas enquanto aguarda o usuário", async () => {
    vi.useFakeTimers({ toFake: ["setInterval", "clearInterval"] });
    const action = vi.fn(async () => INITIAL_OPENAI_ACTION_STATE);
    const { rerender } = render(<OpenAIScreen action={action} connection={connection("DESCONECTADO")} initialState={INITIAL_OPENAI_ACTION_STATE} podeGerir />);
    await act(async () => { vi.advanceTimersByTime(12_000); });
    expect(refresh).not.toHaveBeenCalled();
    rerender(<OpenAIScreen action={action} connection={connection("AGUARDANDO_USUARIO")} initialState={INITIAL_OPENAI_ACTION_STATE} podeGerir />);
    await act(async () => { vi.advanceTimersByTime(3_000); });
    expect(refresh).toHaveBeenCalledTimes(1);
    expect(action).not.toHaveBeenCalled();
    rerender(<OpenAIScreen action={action} connection={connection("CONECTADO")} initialState={INITIAL_OPENAI_ACTION_STATE} podeGerir />);
    await act(async () => { vi.advanceTimersByTime(12_000); });
    expect(refresh).toHaveBeenCalledTimes(1);
  });

  it("revalida imediatamente ao voltar da aba de login e oferece verificação manual", async () => {
    render(<OpenAIScreen action={async () => INITIAL_OPENAI_ACTION_STATE} connection={connection("AGUARDANDO_USUARIO")} initialState={INITIAL_OPENAI_ACTION_STATE} podeGerir />);
    expect(screen.getByText(/atualiza automaticamente quando você volta/i)).toBeInTheDocument();
    fireEvent(document, new Event("visibilitychange"));
    fireEvent.focus(window);
    expect(refresh).toHaveBeenCalledTimes(1);
    await click("Verificar agora");
    expect(refresh).toHaveBeenCalledTimes(2);
  });

  it("não atualiza em aba oculta nem depois do prazo máximo", async () => {
    vi.useFakeTimers({ toFake: ["Date", "setInterval", "clearInterval"] });
    vi.setSystemTime(new Date("2026-09-09T12:00:00Z"));
    const originalVisibility = document.visibilityState;
    Object.defineProperty(document, "visibilityState", { configurable: true, value: "hidden" });
    render(<OpenAIScreen action={async () => INITIAL_OPENAI_ACTION_STATE} connection={connection("AGUARDANDO_USUARIO")} initialState={INITIAL_OPENAI_ACTION_STATE} podeGerir />);
    fireEvent(document, new Event("visibilitychange"));
    fireEvent.focus(window);
    expect(refresh).not.toHaveBeenCalled();
    Object.defineProperty(document, "visibilityState", { configurable: true, value: originalVisibility });
    await act(async () => { vi.advanceTimersByTime(10 * 60_000); });
    refresh.mockReset();
    fireEvent(document, new Event("visibilitychange"));
    fireEvent.focus(window);
    expect(refresh).not.toHaveBeenCalled();
  });

  it("confirma explicitamente quando a conta conectou mesmo com limite atingido", () => {
    render(<OpenAIScreen action={async () => INITIAL_OPENAI_ACTION_STATE} connection={connection("LIMITE_ATINGIDO")} initialState={INITIAL_OPENAI_ACTION_STATE} podeGerir />);
    expect(screen.getByText(/login confirmado.*conta OpenAI está conectada/i)).toBeInTheDocument();
  });

  it("inicia um orçamento novo para login tardio e para a tentativa seguinte", async () => {
    vi.useFakeTimers({ toFake: ["Date", "setInterval", "clearInterval", "setTimeout", "clearTimeout"] });
    vi.setSystemTime(new Date("2026-09-09T12:00:00Z"));
    const action = vi.fn(async () => INITIAL_OPENAI_ACTION_STATE);
    const { rerender } = render(<OpenAIScreen action={action} connection={connection("DESCONECTADO")} initialState={INITIAL_OPENAI_ACTION_STATE} podeGerir />);
    await act(async () => { vi.advanceTimersByTime(12 * 60_000); });
    rerender(<OpenAIScreen action={action} connection={connection("AGUARDANDO_USUARIO")} initialState={INITIAL_OPENAI_ACTION_STATE} podeGerir />);
    await act(async () => { vi.advanceTimersByTime(3_000); });
    expect(refresh).toHaveBeenCalledTimes(1);
    rerender(<OpenAIScreen action={action} connection={connection("DESCONECTADO")} initialState={INITIAL_OPENAI_ACTION_STATE} podeGerir />);
    await act(async () => { vi.advanceTimersByTime(12 * 60_000); });
    rerender(<OpenAIScreen action={action} connection={connection("AGUARDANDO_USUARIO")} initialState={INITIAL_OPENAI_ACTION_STATE} podeGerir />);
    await act(async () => { vi.advanceTimersByTime(3_000); });
    expect(refresh).toHaveBeenCalledTimes(2);
  });

  it("preserva o desafio no diagnóstico, permite cancelar e o oculta ao conectar", () => {
    const challenge = { verificationUrl: "https://auth.openai.com/codex/device", userCode: "KEEP-CODE", expiresAt: "2099-01-01T00:10:00Z" };
    const diagnostic: OpenAIActionState = { kind: "diagnostic", message: "Diagnóstico atualizado.", correlationId: "corr", challenge, diagnostic: { state: "AGUARDANDO_USUARIO", observedAt: "2026-09-09T12:00:00Z", accountStatus: "ok", accountConnected: false, planType: null, modelsStatus: "ok", models: [], rateLimitsStatus: "ok", rateLimits: [] } };
    const { rerender } = render(<OpenAIScreen action={async () => diagnostic} connection={connection("AGUARDANDO_USUARIO")} initialState={diagnostic} podeGerir />);
    expect(screen.getByText("KEEP-CODE")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Cancelar tentativa" })).toBeInTheDocument();
    rerender(<OpenAIScreen action={async () => diagnostic} connection={connection("CONECTADO")} initialState={diagnostic} podeGerir />);
    expect(screen.queryByText("KEEP-CODE")).not.toBeInTheDocument();
  });

  it("vence o código, reconcilia a conexão e aceita uma tentativa com novo prazo", async () => {
    vi.useFakeTimers({ toFake: ["Date", "setInterval", "clearInterval", "setTimeout", "clearTimeout"] });
    vi.setSystemTime(new Date("2026-09-09T12:00:00Z"));
    const first: OpenAIActionState = { kind: "login", message: "Login iniciado.", correlationId: "corr", challenge: { verificationUrl: "https://auth.openai.com/codex/device", userCode: "SAME-CODE", expiresAt: "2026-09-09T12:00:05Z" } };
    const { unmount } = render(<OpenAIScreen action={async () => first} connection={connection("AGUARDANDO_USUARIO")} initialState={first} podeGerir />);
    expect(screen.getByText("SAME-CODE")).toBeInTheDocument();
    await act(async () => { vi.advanceTimersByTime(5_000); });
    expect(screen.queryByText("SAME-CODE")).not.toBeInTheDocument();
    expect(screen.getByText(/código expirou/i)).toBeInTheDocument();
    expect(refresh).toHaveBeenCalled();
    unmount();

    const second: OpenAIActionState = { kind: "login", message: "Login iniciado.", correlationId: "corr-2", challenge: { verificationUrl: "https://auth.openai.com/codex/device", userCode: "SAME-CODE", expiresAt: "2026-09-09T12:01:05Z" } };
    render(<OpenAIScreen action={async () => second} connection={connection("AGUARDANDO_USUARIO")} initialState={second} podeGerir />);
    expect(screen.getByText("SAME-CODE")).toBeInTheDocument();
  });

  it("consulta diagnóstico só pelo clique e bloqueia nova consulta por 60 segundos", async () => {
    vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
    const intents: string[] = [];
    const action = async (_state: OpenAIActionState, data: FormData): Promise<OpenAIActionState> => {
      intents.push(String(data.get("intent")));
      return { kind: "diagnostic", message: "Diagnóstico atualizado.", correlationId: "corr", diagnostic: { state: "CONECTADO", observedAt: "2026-09-09T12:00:00Z", accountStatus: "ok", accountConnected: true, planType: "plus", modelsStatus: "ok", models: [{ id: "gpt-test", displayName: "GPT Test", default: true }], rateLimitsStatus: "ok", rateLimits: [{ limitId: "codex", planType: "plus", primary: { usedPercent: 20, windowDurationMinutes: 300, resetsAt: 1790000000 }, secondary: null }] } };
    };
    const { rerender } = render(<OpenAIScreen action={action} connection={connection("CONECTADO")} initialState={INITIAL_OPENAI_ACTION_STATE} podeGerir />);
    expect(intents).toEqual([]);
    await click("Atualizar diagnóstico");
    expect(intents).toEqual(["diagnostico"]);
    expect(screen.queryByText("GPT Test (padrão)")).not.toBeInTheDocument();
    rerender(<OpenAIScreen
      action={action}
      connection={{
        ...connection("CONECTADO"),
        usageSummary: {
          observedAt: "2026-09-09T12:00:00Z",
          rateLimitsStatus: "ok",
          rateLimits: [{ limitId: "codex", planType: "plus", primary: { usedPercent: 20, windowDurationMinutes: 300, resetsAt: 1790000000 }, secondary: null }],
        },
      }}
      initialState={INITIAL_OPENAI_ACTION_STATE}
      podeGerir
    />);
    expect(screen.getByText("GPT Test (padrão)")).toBeInTheDocument();
    rerender(<OpenAIScreen action={action} connection={connection("CONECTADO")} initialState={INITIAL_OPENAI_ACTION_STATE} podeGerir />);
    expect(screen.queryByText("GPT Test (padrão)")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Diagnóstico disponível em até 60s" })).toBeDisabled();
    await act(async () => { vi.advanceTimersByTime(60_000); });
    expect(screen.getByRole("button", { name: "Atualizar diagnóstico" })).toBeEnabled();
  });

  it("mostra o último limite conhecido sem iniciar diagnóstico automático", () => {
    const action = vi.fn(async () => INITIAL_OPENAI_ACTION_STATE);
    const connected = {
      ...connection("CONECTADO"),
      usageSummary: {
        observedAt: "2026-09-09T12:00:00Z",
        rateLimitsStatus: "ok" as const,
        rateLimits: [{
          limitId: "codex",
          planType: "prolite",
          primary: { usedPercent: 60, windowDurationMinutes: 10_080, resetsAt: 1_790_000_000 },
          secondary: null,
        }],
      },
    };
    render(<OpenAIScreen action={action} connection={connected} initialState={INITIAL_OPENAI_ACTION_STATE} podeGerir />);
    expect(screen.getByText("60% usado", { exact: true })).toBeInTheDocument();
    expect(screen.getByText("40% disponível", { exact: true })).toBeInTheDocument();
    expect(screen.getByRole("progressbar", { name: "60% usado; 40% disponível" })).toHaveAttribute("aria-valuenow", "60");
    expect(action).not.toHaveBeenCalled();
  });

  it("explica que logout é local e envia a intenção correta", async () => {
    const intents: string[] = [];
    const action = async (_state: OpenAIActionState, data: FormData): Promise<OpenAIActionState> => {
      intents.push(String(data.get("intent")));
      return { kind: "logout", message: "Sessão removida.", correlationId: "corr", logout: { state: "DESCONECTADO", localLogout: true, remoteRevocationVerified: false } };
    };
    render(<OpenAIScreen action={action} connection={connection("CONECTADO")} initialState={INITIAL_OPENAI_ACTION_STATE} podeGerir />);
    expect(screen.getByText(/não confirma revogação remota/i)).toBeInTheDocument();
    await click("Desconectar deste ambiente");
    expect(intents).toEqual(["desconectar"]);
  });
});
