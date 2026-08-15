import type { Metadata } from "next";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { DevedoresPage } from "@/components/devedores/devedores";
import { createRuntimeDependencies } from "@/lib/bff/backend.server";
import { recoveryAttemptCookieName } from "@/lib/bff/context.server";
import { currentOperationalContext } from "@/lib/bff/current-context.server";
import { listDevedores } from "@/lib/bff/devedores.server";
import { INITIAL_DEVEDOR_ACTION_STATE, resolveDevedoresFilters } from "@/lib/devedores/devedores-policy";

import { createDevedorAction } from "./actions";

export const metadata: Metadata = {
  title: "Devedores | Frontend MVP",
};

export default async function DevedoresRoute({ searchParams }: PageProps<"/app/devedores">) {
  const query = await searchParams;
  const filters = resolveDevedoresFilters(query);
  const cookieStore = await cookies();
  const dependencies = createRuntimeDependencies();
  const context = await currentOperationalContext();
  const result = await listDevedores(cookieStore, context, filters, dependencies);
  if (result.kind === "problem" && result.problem.status === 401) {
    redirect(cookieStore.get(recoveryAttemptCookieName(dependencies.config)) ? "/login" : "/session/recover");
  }
  return (
    <DevedoresPage
      createAction={createDevedorAction}
      filters={filters}
      initialState={INITIAL_DEVEDOR_ACTION_STATE}
      permissions={context.permissoes}
      recoveryHref={cookieStore.get(recoveryAttemptCookieName(dependencies.config)) ? "/login" : "/session/recover"}
      result={result}
    />
  );
}
