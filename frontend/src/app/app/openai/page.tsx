import type { Metadata } from "next";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { OpenAIScreen } from "@/components/openai/openai.client";
import { createRuntimeDependencies } from "@/lib/bff/backend.server";
import { recoveryAttemptCookieName } from "@/lib/bff/context.server";
import { currentOperationalContext } from "@/lib/bff/current-context.server";
import { readOpenAIConnection } from "@/lib/bff/openai.server";
import { INITIAL_OPENAI_ACTION_STATE, OPENAI_MANAGE_PERMISSION, hasOpenAIPermission } from "@/lib/openai/openai-policy";
import { openAIAction } from "./actions";

export const metadata: Metadata = { title: "Conexão OpenAI | TiaNet" };

export default async function OpenAIRoute() {
  const cookieStore = await cookies();
  const dependencies = createRuntimeDependencies();
  const context = await currentOperationalContext();
  const result = await readOpenAIConnection(cookieStore, context, dependencies);
  if (result.kind === "problem" && result.status === 401) redirect(cookieStore.get(recoveryAttemptCookieName(dependencies.config)) ? "/login" : "/session/recover");
  if (result.kind === "problem") return <section className="grid gap-3"><h1 className="text-xl font-semibold">Conexão OpenAI</h1><p className="rounded-md border border-destructive/40 bg-destructive/5 p-3 text-sm" role="alert">{result.message}<span className="mt-1 block text-xs text-muted-foreground">Correlation ID: {result.correlationId}</span></p></section>;
  return <OpenAIScreen action={openAIAction} connection={result.connection} initialState={INITIAL_OPENAI_ACTION_STATE} podeGerir={hasOpenAIPermission(context.permissoes, OPENAI_MANAGE_PERMISSION)} />;
}
