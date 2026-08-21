import type { ReactNode } from "react";

import type { OperationalContext } from "../../lib/bff/context.server";
import { SHELL_NAVIGATION, visibleNavigationItems } from "../../lib/shell/navigation-policy";

import { ContextSummary } from "./context-summary";
import { MobileNav } from "./mobile-nav.client";
import { Navigation } from "./navigation";

type AppShellProps = Readonly<{ children: ReactNode; context: OperationalContext }>;

export function AppShell({ children, context }: AppShellProps) {
  const navigation = visibleNavigationItems(SHELL_NAVIGATION, context.permissoes);
  return (
    <div className="min-h-screen bg-muted/40">
      <div className="mx-auto grid w-full max-w-(--size-content) gap-5 px-5 py-6 sm:px-8 lg:grid-cols-[15rem_minmax(0,1fr)] lg:px-10 lg:py-8">
        <aside className="content-start gap-5 rounded-xl border border-border bg-background p-4 shadow-sm lg:grid">
          <ContextSummary context={context} />
          <div className="hidden lg:block">
            <Navigation items={navigation} />
          </div>
        </aside>
        <main className="min-w-0" id="conteudo-principal" tabIndex={-1}>
          <MobileNav items={navigation} />
          {children}
        </main>
      </div>
    </div>
  );
}
