import type { Metadata } from "next";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { AutomacaoAdmin } from "@/components/automacao/automacao";
import { ApiProblem, createRuntimeDependencies } from "@/lib/bff/backend.server";
import { beginAutomacaoLoads } from "@/lib/bff/automacao.server";
import { recoveryAttemptCookieName } from "@/lib/bff/context.server";
import { currentOperationalContext } from "@/lib/bff/current-context.server";
import { resolveAutomacaoFilters } from "@/lib/automacao/automacao-policy";

import {
  activateTemplateAction,
  approveTemplateAction,
  cancelJobAction,
  createTemplateAction,
  reconcileNotificationAction,
  retryJobAction,
} from "./actions";

export const metadata: Metadata = {
  title: "Automacao | Frontend MVP",
};

export default async function AutomacaoPage({ searchParams }: PageProps<"/app/automacao">) {
  const filters = resolveAutomacaoFilters(await searchParams);
  const cookieStore = await cookies();
  const dependencies = createRuntimeDependencies();
  const recoveryHref = cookieStore.get(recoveryAttemptCookieName(dependencies.config)) ? "/login" : "/session/recover";
  const context = await currentOperationalContext();
  let loads: Awaited<ReturnType<typeof beginAutomacaoLoads>>;
  try {
    loads = await beginAutomacaoLoads(cookieStore, context, filters, dependencies);
  } catch (error) {
    if (error instanceof ApiProblem && error.status === 401) redirect(recoveryHref);
    throw error;
  }
  return (
    <AutomacaoAdmin
      actions={{
        activateTemplateAction,
        approveTemplateAction,
        cancelJobAction,
        createTemplateAction,
        reconcileNotificationAction,
        retryJobAction,
      }}
      filters={filters}
      permissions={context.permissoes}
      recoveryHref={recoveryHref}
      {...loads}
    />
  );
}
