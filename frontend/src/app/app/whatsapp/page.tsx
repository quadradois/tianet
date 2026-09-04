import type { Metadata } from "next";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { WhatsAppScreen } from "@/components/whatsapp/whatsapp.client";
import { createRuntimeDependencies } from "@/lib/bff/backend.server";
import { recoveryAttemptCookieName } from "@/lib/bff/context.server";
import { currentOperationalContext } from "@/lib/bff/current-context.server";
import { readWhatsAppConnection } from "@/lib/bff/whatsapp.server";
import {
  INITIAL_WHATSAPP_ACTION_STATE,
  WHATSAPP_MANAGE_PERMISSION,
  hasExactPermission,
} from "@/lib/whatsapp/whatsapp-policy";

import { whatsappAction } from "./actions";

export const metadata: Metadata = {
  title: "Conexao do WhatsApp | TiaNet",
};

export default async function WhatsAppRoute() {
  const cookieStore = await cookies();
  const dependencies = createRuntimeDependencies();
  const context = await currentOperationalContext();
  const result = await readWhatsAppConnection(cookieStore, context, dependencies);

  if (result.kind === "problem" && result.status === 401) {
    redirect(cookieStore.get(recoveryAttemptCookieName(dependencies.config)) ? "/login" : "/session/recover");
  }

  if (result.kind === "problem") {
    return (
      <section className="grid gap-3">
        <h1 className="text-xl font-semibold">Conexao do WhatsApp</h1>
        <p className="rounded-md border border-destructive/40 bg-destructive/5 p-3 text-sm" role="alert">
          {result.message}
          <span className="mt-1 block text-xs text-muted-foreground">Correlation ID: {result.correlationId}</span>
        </p>
      </section>
    );
  }

  return (
    <WhatsAppScreen
      action={whatsappAction}
      connection={result.connection}
      initialState={INITIAL_WHATSAPP_ACTION_STATE}
      podeGerir={hasExactPermission(context.permissoes, WHATSAPP_MANAGE_PERMISSION)}
    />
  );
}
