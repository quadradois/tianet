import { describe, expect, it } from "vitest";

import { visibleNavigationItems, type NavigationDestination } from "../../src/lib/shell/navigation-policy";

const destinations: readonly NavigationDestination[] = [
  { href: "/app", label: "Inicio" },
  { href: "/alpha", label: "Alpha", requiredPermission: "permission.alpha" },
  { href: "/beta", label: "Beta", requiredPermission: "permission.beta" },
  { href: "/dashboard", label: "Dashboard", requiredAnyPermission: ["report.read", "agenda.read"] },
];

describe("politica de navegacao", () => {
  it("usa igualdade exata da permissao efetiva", () => {
    expect(visibleNavigationItems(destinations, ["permission.alpha"]).map((item) => item.href)).toEqual(["/app", "/alpha"]);
    expect(visibleNavigationItems(destinations, ["permission.*", "Permission.beta", "permission"])).toEqual([destinations[0]]);
  });

  it("perfil ausente ou lista vazia nao concede destino protegido", () => {
    expect(visibleNavigationItems(destinations, []).map((item) => item.href)).toEqual(["/app"]);
  });

  it("aceita qualquer permissao da lista sem usar prefixo ou wildcard", () => {
    expect(visibleNavigationItems(destinations, ["agenda.read"]).map((item) => item.href)).toEqual(["/app", "/dashboard"]);
    expect(visibleNavigationItems(destinations, ["agenda.*", "Agenda.read"]).map((item) => item.href)).toEqual(["/app"]);
  });

  it("expoe Contratos somente por permissao contratual exata", async () => {
    const { SHELL_NAVIGATION } = await import("../../src/lib/shell/navigation-policy");
    expect(visibleNavigationItems(SHELL_NAVIGATION, ["contratos.contrato.ler"]).map((item) => item.href)).toContain("/app/contratos");
    expect(visibleNavigationItems(SHELL_NAVIGATION, ["contratos.contrato.*", "contratos"]).map((item) => item.href)).not.toContain("/app/contratos");
  });

  it("expoe Motor somente por permissao financeira exata", async () => {
    const { SHELL_NAVIGATION } = await import("../../src/lib/shell/navigation-policy");
    expect(visibleNavigationItems(SHELL_NAVIGATION, ["motor.emprestimo.ler"]).map((item) => item.href)).toContain("/app/motor");
    expect(visibleNavigationItems(SHELL_NAVIGATION, ["motor.emprestimo.*", "motor"]).map((item) => item.href)).not.toContain("/app/motor");
  });

  it("expoe Cobranca somente por permissao exata", async () => {
    const { SHELL_NAVIGATION } = await import("../../src/lib/shell/navigation-policy");
    expect(visibleNavigationItems(SHELL_NAVIGATION, ["cobranca.caso.ler"]).map((item) => item.href)).toContain("/app/cobranca");
    expect(visibleNavigationItems(SHELL_NAVIGATION, ["cobranca.*", "cobranca"]).map((item) => item.href)).not.toContain("/app/cobranca");
  });

  it("expoe Agenda e Comunicacao somente por permissao exata", async () => {
    const { SHELL_NAVIGATION } = await import("../../src/lib/shell/navigation-policy");
    expect(visibleNavigationItems(SHELL_NAVIGATION, ["agenda.ler"]).map((item) => item.href)).toContain("/app/agenda");
    expect(visibleNavigationItems(SHELL_NAVIGATION, ["comunicacao.ler"]).map((item) => item.href)).toContain("/app/agenda");
    expect(visibleNavigationItems(SHELL_NAVIGATION, ["agenda.*", "comunicacao"]).map((item) => item.href)).not.toContain("/app/agenda");
  });

  it("expoe Relatorios somente por permissao exata", async () => {
    const { SHELL_NAVIGATION } = await import("../../src/lib/shell/navigation-policy");
    expect(visibleNavigationItems(SHELL_NAVIGATION, ["relatorios.operacionais.ler"]).map((item) => item.href)).toContain("/app/relatorios");
    expect(visibleNavigationItems(SHELL_NAVIGATION, ["relatorios.operacionais.*", "Relatorios.operacionais.ler"]).map((item) => item.href)).not.toContain("/app/relatorios");
  });

  it("expoe Configuracoes Financeiras somente por permissao exata", async () => {
    const { SHELL_NAVIGATION } = await import("../../src/lib/shell/navigation-policy");
    expect(visibleNavigationItems(SHELL_NAVIGATION, ["configuracoes_financeiras.configuracao.ler"]).map((item) => item.href)).toContain("/app/configuracoes-financeiras");
    expect(visibleNavigationItems(SHELL_NAVIGATION, ["configuracoes_financeiras.configuracao.*", "configuracoes_financeiras"]).map((item) => item.href)).not.toContain("/app/configuracoes-financeiras");
  });

  it("expoe IAM somente por permissao exata de Perfil", async () => {
    const { SHELL_NAVIGATION } = await import("../../src/lib/shell/navigation-policy");
    expect(visibleNavigationItems(SHELL_NAVIGATION, ["perfil.ler"]).map((item) => item.href)).toContain("/app/iam");
    expect(visibleNavigationItems(SHELL_NAVIGATION, ["perfil.gerir"]).map((item) => item.href)).toContain("/app/iam");
    expect(visibleNavigationItems(SHELL_NAVIGATION, ["perfil.*", "perfil"]).map((item) => item.href)).not.toContain("/app/iam");
  });

  it("expoe Automacao somente por permissao exata", async () => {
    const { SHELL_NAVIGATION } = await import("../../src/lib/shell/navigation-policy");
    expect(visibleNavigationItems(SHELL_NAVIGATION, ["automacao.job.consultar"]).map((item) => item.href)).toContain("/app/automacao");
    expect(visibleNavigationItems(SHELL_NAVIGATION, ["notificacao.template.gerir"]).map((item) => item.href)).toContain("/app/automacao");
    expect(visibleNavigationItems(SHELL_NAVIGATION, ["automacao.*", "notificacao"]).map((item) => item.href)).not.toContain("/app/automacao");
  });
});
