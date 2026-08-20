import type { Metadata } from "next";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { MotorPage } from "@/components/motor/motor";
import { createRuntimeDependencies } from "@/lib/bff/backend.server";
import { recoveryAttemptCookieName } from "@/lib/bff/context.server";
import { currentOperationalContext } from "@/lib/bff/current-context.server";
import { listDevedores } from "@/lib/bff/devedores.server";
import { listLoans } from "@/lib/bff/motor.server";
import { INITIAL_MOTOR_ACTION_STATE, isUuid, resolveLoanFilters } from "@/lib/motor/motor-policy";

import { createLoanAction } from "./actions";

export const metadata: Metadata = {
  title: "Motor | Frontend MVP",
};

export default async function MotorRoute({ searchParams }: PageProps<"/app/motor">) {
  const query = await searchParams;
  const filters = resolveLoanFilters(query);
  const cookieStore = await cookies();
  const dependencies = createRuntimeDependencies();
  const context = await currentOperationalContext();
  const [result, devedoresResult] = await Promise.all([
    listLoans(cookieStore, context, filters, dependencies),
    // Uma chamada para toda a pagina, nunca uma por emprestimo. Sem nome, a
    // lista voltaria a identificar o Devedor por UUID.
    listDevedores(cookieStore, context, { page: 1, size: 100 }, dependencies),
  ]);
  if (result.kind === "problem" && result.problem.status === 401) {
    redirect(cookieStore.get(recoveryAttemptCookieName(dependencies.config)) ? "/login" : "/session/recover");
  }
  // Falta de permissao de Devedor degrada o rotulo, nunca a lista de emprestimos.
  const devedores = new Map<string, string>(
    devedoresResult.kind === "ready" && "items" in devedoresResult.data
      ? devedoresResult.data.items.map((devedor) => [devedor.id, devedor.nome])
      : [],
  );
  const contractCandidate = typeof query.contrato_id === "string" ? query.contrato_id : undefined;
  return (
    <MotorPage
      createAction={createLoanAction}
      devedores={devedores}
      filters={filters}
      initialContractId={contractCandidate && isUuid(contractCandidate) ? contractCandidate : undefined}
      initialState={INITIAL_MOTOR_ACTION_STATE}
      permissions={context.permissoes}
      recoveryHref={cookieStore.get(recoveryAttemptCookieName(dependencies.config)) ? "/login" : "/session/recover"}
      result={result}
    />
  );
}
