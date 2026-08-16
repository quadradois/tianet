import type { Metadata } from "next";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { MotorDetailPage } from "@/components/motor/motor";
import { createRuntimeDependencies } from "@/lib/bff/backend.server";
import { recoveryAttemptCookieName } from "@/lib/bff/context.server";
import { currentOperationalContext } from "@/lib/bff/current-context.server";
import { getBalance, getInstallments, getLoan, getMemories, getSettlementPreview } from "@/lib/bff/motor.server";
import { INITIAL_MOTOR_ACTION_STATE, type Balance, type CalculationMemory, type InstallmentPlan, type MotorReadResult, type SettlementPreview } from "@/lib/motor/motor-policy";

import {
  executeSettlementAction,
  generateInstallmentsAction,
  registerPaymentAction,
  registerRenegotiationAction,
} from "../actions";

export const metadata: Metadata = {
  title: "Emprestimo | Frontend MVP",
};

function referenceDate(query: Readonly<Record<string, string | readonly string[] | undefined>>): string {
  return typeof query.data_referencia === "string" && /^\d{4}-\d{2}-\d{2}$/.test(query.data_referencia)
    ? query.data_referencia
    : "2026-08-14";
}

function denied<T>(): MotorReadResult<T> {
  return { kind: "denied" };
}

export default async function MotorDetailRoute({ params, searchParams }: PageProps<"/app/motor/[emprestimoId]">) {
  const { emprestimoId } = await params;
  const query = await searchParams;
  const cookieStore = await cookies();
  const dependencies = createRuntimeDependencies();
  const context = await currentOperationalContext();
  const recoveryHref = cookieStore.get(recoveryAttemptCookieName(dependencies.config)) ? "/login" : "/session/recover";
  const loan = await getLoan(cookieStore, context, emprestimoId, dependencies);
  if (loan.kind === "problem" && loan.problem.status === 401) redirect(recoveryHref);
  const selectedDate = referenceDate(query);
  const [installments, balance, memories, settlement] = loan.kind === "ready"
    ? await Promise.all([
      getInstallments(cookieStore, context, emprestimoId, dependencies),
      getBalance(cookieStore, context, emprestimoId, selectedDate, dependencies),
      getMemories(cookieStore, context, emprestimoId, dependencies),
      getSettlementPreview(cookieStore, context, emprestimoId, selectedDate, dependencies),
    ])
    : [
      denied<InstallmentPlan>(),
      denied<Balance>(),
      denied<readonly CalculationMemory[]>(),
      denied<SettlementPreview>(),
    ];
  for (const result of [installments, balance, memories, settlement]) {
    if (result.kind === "problem" && result.problem.status === 401) redirect(recoveryHref);
  }
  return (
    <MotorDetailPage
      balance={balance}
      generateInstallmentsAction={generateInstallmentsAction}
      initialState={INITIAL_MOTOR_ACTION_STATE}
      installments={installments}
      loan={loan}
      memories={memories}
      paymentAction={registerPaymentAction}
      permissions={context.permissoes}
      recoveryHref={recoveryHref}
      renegotiationAction={registerRenegotiationAction}
      settlementAction={executeSettlementAction}
      settlementPreview={settlement}
    />
  );
}
