import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { LoginForm } from "../../src/components/auth/login-form.client";
import { LogoutButton } from "../../src/components/auth/logout-button.client";
import { AppShell } from "../../src/components/shell/app-shell";
import type { OperationalContext } from "../../src/lib/bff/context.server";

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
