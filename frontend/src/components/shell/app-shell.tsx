import type { ReactNode } from "react";

import type { OperationalContext } from "../../lib/bff/context.server";
import { SHELL_NAVIGATION, visibleNavigationItems } from "../../lib/shell/navigation-policy";

import { ContextSummary } from "./context-summary";
import { Navigation } from "./navigation";

type AppShellProps = Readonly<{ children: ReactNode; context: OperationalContext }>;

export function AppShell({ children, context }: AppShellProps) {
  const navigation = visibleNavigationItems(SHELL_NAVIGATION, context.permissoes);
  return (
    <div className="grid min-h-screen bg-muted/40 lg:grid-cols-[15rem_minmax(0,1fr)]">
      <aside className="content-start gap-5 rounded-xl border border-border bg-background p-4 shadow-sm lg:grid">
        <ContextSummary context={context} />
        <Navigation items={navigation} />
      </aside>
      <main className="min-w-0" id="conteudo-principal" tabIndex={-1}>{children}</main>
    </div>
  );
}
