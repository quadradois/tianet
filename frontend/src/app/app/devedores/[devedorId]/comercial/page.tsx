import type { Metadata } from "next";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { ComercialDevedorPage } from "@/components/comercial/comercial";
import { createRuntimeDependencies } from "@/lib/bff/backend.server";
import { recoveryAttemptCookieName } from "@/lib/bff/context.server";
import { currentOperationalContext } from "@/lib/bff/current-context.server";
import { listCommercialProposals } from "@/lib/bff/comercial.server";
import { INITIAL_COMERCIAL_ACTION_STATE, resolveProposalFilters } from "@/lib/comercial/comercial-policy";

import { createProposalAction, createSimulationAction } from "../../../comercial/actions";

export const metadata: Metadata = {
  title: "Comercial do Devedor | Frontend MVP",
};

export default async function ComercialDevedorRoute({ params, searchParams }: PageProps<"/app/devedores/[devedorId]/comercial">) {
  const { devedorId } = await params;
  const query = await searchParams;
  const filters = resolveProposalFilters(query);
  const cookieStore = await cookies();
  const dependencies = createRuntimeDependencies();
  const context = await currentOperationalContext();
  const proposals = await listCommercialProposals(cookieStore, context, devedorId, filters, dependencies);
  if (proposals.kind === "problem" && proposals.problem.status === 401) {
    redirect(cookieStore.get(recoveryAttemptCookieName(dependencies.config)) ? "/login" : "/session/recover");
  }
  return (
    <ComercialDevedorPage
      createProposalAction={createProposalAction}
      createSimulationAction={createSimulationAction}
      devedorId={devedorId}
      filters={filters}
      initialState={INITIAL_COMERCIAL_ACTION_STATE}
      permissions={context.permissoes}
      proposals={proposals}
      recoveryHref={cookieStore.get(recoveryAttemptCookieName(dependencies.config)) ? "/login" : "/session/recover"}
    />
  );
}
