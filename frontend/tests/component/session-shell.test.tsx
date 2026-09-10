import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { LoginForm } from "../../src/components/auth/login-form.client";
import { LogoutButton } from "../../src/components/auth/logout-button.client";
import { AppShell } from "../../src/components/shell/app-shell";
import { OpenAIBadge, OpenAIBadgePending } from "../../src/components/shell/openai-badge";
import type { OperationalContext } from "../../src/lib/bff/context.server";
import type { OpenAIReadResult } from "../../src/lib/openai/openai-policy";

const replace = vi.fn();
const refresh = vi.fn();

vi.mock("next/navigation", () => ({ useRouter: () => ({ replace, refresh }), usePathname: () => "/app" }));

const context: OperationalContext = {
  carteira_padrao: { id: "carteira-1", nome: "Carteira Centro" },
  perfil: null,
  permissoes: [],
  tenant: { id: "tenant-1", identificador_institucional: "ACME", nome: "Instituicao ACME" },
  usuario: { email: "operador@example.test", id: "usuario-1", nome: "Operador" },
  whatsapp: { alerta_queda_ativa: false, numero: null, pareada: false, queda_detectada_em: null },
};

const contextQuedaAtiva: OperationalContext = {
  ...context,
  whatsapp: { alerta_queda_ativa: true, numero: null, pareada: false, queda_detectada_em: "2026-09-08T12:00:00.000Z" },
};

const openAIConnected: OpenAIReadResult = {
  kind: "ready",
  connection: {
    enabled: true,
    processAvailable: true,
    accountConnected: true,
    planType: "prolite",
    state: "CONECTADO",
    usageSummary: {
      observedAt: "2026-09-10T04:29:01Z",
      rateLimitsStatus: "ok",
      rateLimits: [{ limitId: "codex", planType: "prolite", primary: { usedPercent: 60, windowDurationMinutes: 10_080, resetsAt: 1790000000 }, secondary: null }],
    },
  },
};

describe("login e shell", () => {
  beforeEach(() => { vi.restoreAllMocks(); replace.mockReset(); refresh.mockReset(); });

  it("envia somente credenciais ao BFF e navega para destino fixo", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(Response.json({ authenticated: true, correlationId: "corr-login" }));
    const user = userEvent.setup();
    render(<LoginForm />);
    expect(screen.queryByRole("textbox", { name: "Instituicao" })).not.toBeInTheDocument();
    await user.type(screen.getByRole("textbox", { name: "E-mail" }), "operador@example.test");
    await user.type(screen.getByLabelText("Senha"), "segredo");
    await user.click(screen.getByRole("button", { name: "Entrar" }));
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/app"));
    const request = fetchMock.mock.calls[0];
    expect(request?.[0]).toBe("/api/auth/login");
    const init = request?.[1];
    expect(init?.method).toBe("POST");
    expect(JSON.parse(String(init?.body))).toEqual({
      email: "operador@example.test",
      segredo: "segredo",
    });
    expect(String(init?.body)).not.toMatch(/identificador_institucional|tenant|carteira|usuario_id|access_token|refresh_token/);
  });

  it("apresenta Tenant, Carteira e perfil nulo sem fabricar permissao ou navegacao", () => {
    render(<AppShell context={context}><h1>Dashboard</h1></AppShell>);
    expect(screen.getByRole("heading", { name: "Dashboard" })).toBeInTheDocument();
    expect(screen.getByText("Instituicao ACME")).toBeInTheDocument();
    expect(screen.getByText("Carteira Centro")).toBeInTheDocument();
    expect(screen.getByText("Sem perfil ativo")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Dashboard" })).not.toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(/access-token|refresh-token|devedores/i);
  });

  it("exibe a tela inicial somente com ao menos uma permissao exata", () => {
    render(<AppShell context={{ ...context, perfil: { id: "perfil-1", nome: "Operador" }, permissoes: ["agenda.ler"] }}><h1>Inicio</h1></AppShell>);
    expect(screen.getByRole("link", { name: "Inicio" })).toHaveAttribute("href", "/app");
  });

  it("mantem o dia a dia a vista e recolhe a administracao, sem perder destino", () => {
    render(
      <AppShell context={{ ...context, perfil: { id: "perfil-1", nome: "Operador" }, permissoes: ["agenda.ler", "devedor.ler", "perfil.ler"] }}>
        <h1>Inicio</h1>
      </AppShell>,
    );
    // Dia a dia: sempre visivel.
    expect(screen.getByRole("link", { name: "Inicio" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Devedores" })).toBeInTheDocument();
    // Mais ferramentas: recolhida, porem presente — esconder nao e remover, e a
    // tela continua alcancavel para quem tem a permissao.
    expect(screen.getByText("Mais ferramentas")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "IAM" })).toHaveAttribute("href", "/app/iam");
  });

  it("exibe OpenAI como selo inteligente e o remove de Mais ferramentas", () => {
    render(
      <AppShell
        context={{ ...context, permissoes: ["openai.conexao.ler"] }}
        openaiBadge={<OpenAIBadge result={openAIConnected} />}
      >
        <h1>Inicio</h1>
      </AppShell>,
    );
    const badge = screen.getByRole("link", { name: /OpenAI conectado\s*Plano prolite\s*Maior uso: 60%/i });
    expect(badge).toHaveAttribute("href", "/app/openai");
    expect(within(badge).getByText(/^Dados de /)).toBeInTheDocument();
    expect(within(screen.getByRole("navigation")).queryByText("OpenAI")).not.toBeInTheDocument();
  });

  it("nao revela o selo OpenAI sem permissao de leitura", () => {
    render(<AppShell context={context}><h1>Inicio</h1></AppShell>);
    expect(screen.queryByRole("link", { name: /OpenAI/i })).not.toBeInTheDocument();
  });

  it("explica indisponibilidade e limite diretamente no selo OpenAI", () => {
    const authorized = { ...context, permissoes: ["openai.conexao.ler"] };
    const unavailable: OpenAIReadResult = {
      kind: "problem", message: "indisponível", status: 502, correlationId: "corr-openai",
    };
    const { rerender } = render(
      <AppShell context={authorized} openaiBadge={<OpenAIBadge result={unavailable} />}><h1>Inicio</h1></AppShell>,
    );
    expect(screen.getByRole("link", { name: /OpenAI indisponível\s*Verificar conexão/i })).toBeInTheDocument();

    rerender(
      <AppShell
        context={authorized}
        openaiBadge={<OpenAIBadge result={{
          kind: "ready",
          connection: { enabled: true, processAvailable: true, accountConnected: true, planType: "prolite", state: "LIMITE_ATINGIDO", usageSummary: null },
        }} />}
      >
        <h1>Inicio</h1>
      </AppShell>,
    );
    expect(screen.getByRole("link", { name: /OpenAI conectado\s*Limite de uso atingido/i })).toBeInTheDocument();

    rerender(
      <AppShell
        context={authorized}
        openaiBadge={<OpenAIBadge result={{
          kind: "ready",
          connection: {
            enabled: true,
            processAvailable: true,
            accountConnected: true,
            planType: "prolite",
            state: "CONECTADO",
            usageSummary: { observedAt: "2026-09-10T04:29:01Z", rateLimitsStatus: "error", rateLimits: [] },
          },
        }} />}
      >
        <h1>Inicio</h1>
      </AppShell>,
    );
    expect(screen.getByRole("link", { name: /OpenAI conectado\s*Plano prolite\s*Limites indisponíveis\s*Dados de/i })).toBeInTheDocument();

    rerender(
      <AppShell
        context={authorized}
        openaiBadge={<OpenAIBadge result={{
          kind: "ready",
          connection: {
            enabled: true,
            processAvailable: true,
            accountConnected: true,
            planType: "prolite",
            state: "CONECTADO",
            usageSummary: { observedAt: "2026-09-10T04:29:01Z", rateLimitsStatus: "ok", rateLimits: [] },
          },
        }} />}
      >
        <h1>Inicio</h1>
      </AppShell>,
    );
    expect(screen.getByRole("link", { name: /OpenAI conectado\s*Plano prolite\s*Nenhuma janela informada\s*Dados de/i })).toBeInTheDocument();
  });

  it("mantem o acesso OpenAI legivel enquanto o snapshot carrega", () => {
    render(<OpenAIBadgePending />);
    expect(screen.getByRole("link", { name: /OpenAI\s*Verificando conexão/i })).toHaveAttribute("href", "/app/openai");
  });

  it("remove PII da tela depois que o logout local encerra a sessao mesmo com backend 5xx", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(Response.json(
      { codigo: "backend_indisponivel", mensagem: "indisponivel" },
      { status: 502 },
    ));
    render(<LogoutButton />);
    await userEvent.click(screen.getByRole("button", { name: "Sair" }));
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/login"));
    expect(refresh).toHaveBeenCalledOnce();
  });

  it("nao renderiza banner quando o alerta esta inativo e mantem o selo", () => {
    render(<AppShell context={context}><h1>Dashboard</h1></AppShell>);
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.getByText("WhatsApp nao conectado")).toBeInTheDocument();
  });

  it("exibe banner global de queda com link e sem dispensa quando o alerta esta ativo", () => {
    render(<AppShell context={contextQuedaAtiva}><h1>Dashboard</h1></AppShell>);
    const banner = screen.getByRole("alert");
    expect(banner).toHaveTextContent("Conexão do WhatsApp caiu");
    expect(banner).toHaveTextContent("Queda detectada em");
    expect(banner.querySelector("time")?.getAttribute("dateTime")).toBe("2026-09-08T12:00:00.000Z");
    const link = screen.getByRole("link", { name: "Abrir conexão do WhatsApp" });
    expect(link).toHaveAttribute("href", "/app/whatsapp");
    expect(banner.querySelector("button")).toBeNull();
    // O selo conserva sua funcao atual mesmo com o banner visivel.
    expect(screen.getByText("WhatsApp nao conectado")).toBeInTheDocument();
    // Alcancavel por teclado: link nativo entra na ordem de foco sem mouse.
    link.focus();
    expect(link).toHaveFocus();
  });

  it("formata o momento da queda no fuso America/Sao_Paulo", () => {
    render(<AppShell context={contextQuedaAtiva}><h1>Dashboard</h1></AppShell>);
    const esperado = new Intl.DateTimeFormat("pt-BR", {
      dateStyle: "medium",
      timeStyle: "short",
      timeZone: "America/Sao_Paulo",
    }).format(new Date("2026-09-08T12:00:00.000Z"));
    // 12:00Z equivale a 09:00 em Sao Paulo (UTC-3, sem horario de verao).
    expect(esperado).toMatch(/09:00/);
    expect(screen.getByRole("alert").querySelector("time")?.textContent).toBe(esperado);
  });

  it("remove o banner quando o contexto seguinte traz a reconexao", () => {
    const { rerender } = render(<AppShell context={contextQuedaAtiva}><h1>Dashboard</h1></AppShell>);
    expect(screen.getByRole("alert")).toBeInTheDocument();
    rerender(<AppShell context={context}><h1>Dashboard</h1></AppShell>);
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
