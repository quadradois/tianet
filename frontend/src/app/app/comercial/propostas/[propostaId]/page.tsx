import type { Metadata } from "next";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { PropostaComercialPage } from "@/components/comercial/comercial";
import { createRuntimeDependencies } from "@/lib/bff/backend.server";
import { recoveryAttemptCookieName } from "@/lib/bff/context.server";
import { currentOperationalContext } from "@/lib/bff/current-context.server";
import { getApprovedProposalContract, getCommercialProposal, getCommercialSimulation } from "@/lib/bff/comercial.server";
import { INITIAL_COMERCIAL_ACTION_STATE } from "@/lib/comercial/comercial-policy";

import { decideProposalAction, updateProposalAction } from "../../actions";

export const metadata: Metadata = {
  title: "Proposta Comercial | TiaNet",
};

export default async function PropostaComercialRoute({ params }: PageProps<"/app/comercial/propostas/[propostaId]">) {
  const { propostaId } = await params;
  const cookieStore = await cookies();
  const dependencies = createRuntimeDependencies();
  const context = await currentOperationalContext();
  const proposal = await getCommercialProposal(cookieStore, context, propostaId, dependencies);
  if (proposal.kind === "problem" && proposal.problem.status === 401) {
    redirect(cookieStore.get(recoveryAttemptCookieName(dependencies.config)) ? "/login" : "/session/recover");
  }
  const simulation = proposal.kind === "ready" && proposal.data.simulacao_id
    ? await getCommercialSimulation(cookieStore, context, proposal.data.simulacao_id, dependencies, proposal.data.devedor_id)
    : { kind: "denied" as const };
  if (simulation.kind === "problem" && simulation.problem.status === 401) {
    redirect(cookieStore.get(recoveryAttemptCookieName(dependencies.config)) ? "/login" : "/session/recover");
  }
  const contract = proposal.kind === "ready" && proposal.data.estado === "aprovada"
    ? await getApprovedProposalContract(cookieStore, context, propostaId, dependencies)
    : { kind: "denied" as const };
  if (contract.kind === "problem" && contract.problem.status === 401) {
    redirect(cookieStore.get(recoveryAttemptCookieName(dependencies.config)) ? "/login" : "/session/recover");
  }
  return (
    <PropostaComercialPage
      contract={contract}
      decisionAction={decideProposalAction}
      initialState={INITIAL_COMERCIAL_ACTION_STATE}
      permissions={context.permissoes}
      proposal={proposal}
      recoveryHref={cookieStore.get(recoveryAttemptCookieName(dependencies.config)) ? "/login" : "/session/recover"}
      simulation={simulation}
      updateAction={updateProposalAction}
    />
  );
}
