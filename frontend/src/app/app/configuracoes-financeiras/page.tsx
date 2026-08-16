import type { Metadata } from "next";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { ConfiguracoesFinanceiras } from "@/components/configuracoes-financeiras/configuracoes-financeiras";
import { ApiProblem, createRuntimeDependencies } from "@/lib/bff/backend.server";
import { beginConfiguracoesLoads } from "@/lib/bff/configuracoes-financeiras.server";
import { recoveryAttemptCookieName } from "@/lib/bff/context.server";
import { currentOperationalContext } from "@/lib/bff/current-context.server";
import { resolveConfiguracoesFilters } from "@/lib/configuracoes-financeiras/configuracoes-policy";

import {
  activateConfiguracaoAction,
  approveConfiguracaoAction,
  captureSnapshotAction,
  createCalendarioAction,
  createConfiguracaoAction,
  createModalidadeAction,
  inactivateConfiguracaoAction,
  programConfiguracaoAction,
} from "./actions";

export const metadata: Metadata = {
  title: "Configuracoes Financeiras | Frontend MVP",
};

export default async function ConfiguracoesFinanceirasPage({ searchParams }: PageProps<"/app/configuracoes-financeiras">) {
  const query = await searchParams;
  const filters = resolveConfiguracoesFilters(query);
  const cookieStore = await cookies();
  const dependencies = createRuntimeDependencies();
  const recoveryHref = cookieStore.get(recoveryAttemptCookieName(dependencies.config)) ? "/login" : "/session/recover";
  const context = await currentOperationalContext();
  let loads: Awaited<ReturnType<typeof beginConfiguracoesLoads>>;
  try {
    loads = await beginConfiguracoesLoads(cookieStore, context, filters, dependencies);
  } catch (error) {
    if (error instanceof ApiProblem && error.status === 401) redirect(recoveryHref);
    throw error;
  }
  return (
    <ConfiguracoesFinanceiras
      {...loads}
      actions={{
        activateAction: activateConfiguracaoAction,
        approveAction: approveConfiguracaoAction,
        captureSnapshotAction,
        createCalendarioAction,
        createConfiguracaoAction,
        createModalidadeAction,
        inactivateAction: inactivateConfiguracaoAction,
        programAction: programConfiguracaoAction,
      }}
      filters={filters}
      permissions={context.permissoes}
      recoveryHref={recoveryHref}
    />
  );
}
