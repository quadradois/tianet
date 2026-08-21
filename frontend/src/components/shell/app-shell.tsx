import type { ReactNode } from "react";

import { LogoutButton } from "../auth/logout-button.client";
import type { OperationalContext } from "../../lib/bff/context.server";
import { SHELL_NAVIGATION, visibleNavigationItems } from "../../lib/shell/navigation-policy";

import { ContextSummary } from "./context-summary";
import { Navigation } from "./navigation";

type AppShellProps = Readonly<{ children: ReactNode; context: OperationalContext }>;

export function AppShell({ children, context }: AppShellProps) {
  const navigation = visibleNavigationItems(SHELL_NAVIGATION, context.permissoes);
  return (
    <div className="min-h-dvh bg-muted/40">
      <header className="border-b border-border bg-background">
        <div className="mx-auto flex w-full max-w-(--size-content) items-center justify-between gap-4 px-5 py-4 sm:px-8 lg:px-10">
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">TiaNet</p>
            <p className="truncate text-sm font-medium" title={context.usuario.email}>{context.usuario.nome}</p>
          </div>
          <LogoutButton />
        </div>
      </header>
      <div className="mx-auto grid w-full max-w-(--size-content) gap-5 px-5 py-6 sm:px-8 lg:grid-cols-[15rem_minmax(0,1fr)] lg:px-10 lg:py-8">
        <aside className="grid content-start gap-5 rounded-xl border border-border bg-background p-4 shadow-sm">
          <ContextSummary context={context} />
          <Navigation items={navigation} />
        </aside>
        <main className="min-w-0" id="conteudo-principal" tabIndex={-1}>{children}</main>
      </div>
    </div>
  );
}
