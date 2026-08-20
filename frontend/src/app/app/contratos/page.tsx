import type { Metadata } from "next";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { ContratosPage } from "@/components/contratos/contratos";
import { createRuntimeDependencies } from "@/lib/bff/backend.server";
import { recoveryAttemptCookieName } from "@/lib/bff/context.server";
import { currentOperationalContext } from "@/lib/bff/current-context.server";
import { listContracts } from "@/lib/bff/contratos.server";
import { INITIAL_CONTRATO_ACTION_STATE, isUuid, resolveContractFilters } from "@/lib/contratos/contratos-policy";

import { createContractAction } from "./actions";

export const metadata: Metadata = {
  title: "Contratos | TiaNet",
};

export default async function ContratosRoute({ searchParams }: PageProps<"/app/contratos">) {
  const query = await searchParams;
  const cookieStore = await cookies();
  const dependencies = createRuntimeDependencies();
  const context = await currentOperationalContext();
  const filters = resolveContractFilters(query);
  const result = await listContracts(cookieStore, context, filters, dependencies);
  if (result.kind === "problem" && result.problem.status === 401) {
    redirect(cookieStore.get(recoveryAttemptCookieName(dependencies.config)) ? "/login" : "/session/recover");
  }
  const proposalCandidate = typeof query.proposta_id === "string" ? query.proposta_id : undefined;
  return (
    <ContratosPage
      createAction={createContractAction}
      filters={filters}
      initialProposalId={proposalCandidate && isUuid(proposalCandidate) ? proposalCandidate : undefined}
      initialState={INITIAL_CONTRATO_ACTION_STATE}
      permissions={context.permissoes}
      recoveryHref={cookieStore.get(recoveryAttemptCookieName(dependencies.config)) ? "/login" : "/session/recover"}
      result={result}
    />
  );
}
