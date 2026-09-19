import type { Metadata } from "next";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { AgentScreen } from "@/components/agent/agent-screen";
import { createRuntimeDependencies } from "@/lib/bff/backend.server";
import { recoveryAttemptCookieName } from "@/lib/bff/context.server";
import { currentOperationalContext } from "@/lib/bff/current-context.server";
import { readAgentInbox } from "@/lib/bff/agent.server";

export const metadata: Metadata = {
  title: "Agente | TiaNet",
};

export default async function AgentRoute() {
  const cookieStore = await cookies();
  const dependencies = createRuntimeDependencies();
  const context = await currentOperationalContext();
  const result = await readAgentInbox(cookieStore, context, dependencies);

  if (result.kind === "problem" && result.status === 401) {
    redirect(cookieStore.get(recoveryAttemptCookieName(dependencies.config)) ? "/login" : "/session/recover");
  }

  if (result.kind === "problem") {
    return (
      <section className="grid gap-3">
        <h1 className="text-xl font-semibold">Agente</h1>
        <p className="rounded-md border border-destructive/40 bg-destructive/5 p-3 text-sm" role="alert">
          {result.message}
          <span className="mt-1 block text-xs text-muted-foreground">Correlation ID: {result.correlationId}</span>
        </p>
      </section>
    );
  }

  return <AgentScreen inbox={result.inbox} />;
}
