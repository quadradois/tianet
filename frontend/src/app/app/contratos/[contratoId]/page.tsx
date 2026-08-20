import type { Metadata } from "next";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { ContratoDetailPage } from "@/components/contratos/contratos";
import { createRuntimeDependencies } from "@/lib/bff/backend.server";
import { recoveryAttemptCookieName } from "@/lib/bff/context.server";
import { currentOperationalContext } from "@/lib/bff/current-context.server";
import { getContract, getContractHistory } from "@/lib/bff/contratos.server";
import { INITIAL_CONTRATO_ACTION_STATE } from "@/lib/contratos/contratos-policy";

import { decideContractAction } from "../actions";

export const metadata: Metadata = {
  title: "Contrato | TiaNet",
};

export default async function ContratoRoute({ params }: PageProps<"/app/contratos/[contratoId]">) {
  const { contratoId } = await params;
  const cookieStore = await cookies();
  const dependencies = createRuntimeDependencies();
  const context = await currentOperationalContext();
  const contract = await getContract(cookieStore, context, contratoId, dependencies);
  if (contract.kind === "problem" && contract.problem.status === 401) {
    redirect(cookieStore.get(recoveryAttemptCookieName(dependencies.config)) ? "/login" : "/session/recover");
  }
  const history = contract.kind === "ready"
    ? await getContractHistory(cookieStore, context, contratoId, dependencies)
    : { kind: "denied" as const };
  if (history.kind === "problem" && history.problem.status === 401) {
    redirect(cookieStore.get(recoveryAttemptCookieName(dependencies.config)) ? "/login" : "/session/recover");
  }
  return (
    <ContratoDetailPage
      action={decideContractAction}
      contract={contract}
      history={history}
      initialState={INITIAL_CONTRATO_ACTION_STATE}
      permissions={context.permissoes}
      recoveryHref={cookieStore.get(recoveryAttemptCookieName(dependencies.config)) ? "/login" : "/session/recover"}
    />
  );
}
