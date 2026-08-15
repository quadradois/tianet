import type { Metadata } from "next";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { CobrancaPage } from "@/components/cobranca/cobranca";
import { createRuntimeDependencies } from "@/lib/bff/backend.server";
import { recoveryAttemptCookieName } from "@/lib/bff/context.server";
import { currentOperationalContext } from "@/lib/bff/current-context.server";
import { listCollectionCases } from "@/lib/bff/cobranca.server";
import { INITIAL_COBRANCA_ACTION_STATE, resolveCollectionFilters } from "@/lib/cobranca/cobranca-policy";

import { appropriatePromiseAction, registerCollectionActionAction, registerPromiseAction } from "./actions";

export const metadata: Metadata = {
  title: "Cobranca | Frontend MVP",
};

export default async function CobrancaRoute({ searchParams }: PageProps<"/app/cobranca">) {
  const query = await searchParams;
  const filters = resolveCollectionFilters(query);
  const cookieStore = await cookies();
  const dependencies = createRuntimeDependencies();
  const context = await currentOperationalContext();
  const result = await listCollectionCases(cookieStore, context, filters, dependencies);
  if (result.kind === "problem" && result.problem.status === 401) {
    redirect(cookieStore.get(recoveryAttemptCookieName(dependencies.config)) ? "/login" : "/session/recover");
  }
  return (
    <CobrancaPage
      actionState={INITIAL_COBRANCA_ACTION_STATE}
      appropriatePaymentAction={appropriatePromiseAction}
      filters={filters}
      permissions={context.permissoes}
      registerAction={registerCollectionActionAction}
      registerPromiseAction={registerPromiseAction}
      recoveryHref={cookieStore.get(recoveryAttemptCookieName(dependencies.config)) ? "/login" : "/session/recover"}
      result={result}
    />
  );
}
