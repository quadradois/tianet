import type { Metadata } from "next";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { MotorDetailPage } from "@/components/motor/motor";
import { createRuntimeDependencies } from "@/lib/bff/backend.server";
import { recoveryAttemptCookieName } from "@/lib/bff/context.server";
import { currentOperationalContext } from "@/lib/bff/current-context.server";
import { getDevedor } from "@/lib/bff/devedores.server";
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

/**
 * Data usada para perguntar o saldo ao backend.
 *
 * O padrao era a constante "2026-08-14", o que fazia o painel anunciar "ainda
 * falta receber em 14/08/2026" — data anterior ao proprio emprestimo. Passa a
 * ser hoje, no servidor: o navegador nao escolhe data de calculo financeiro.
 */
function referenceDate(query: Readonly<Record<string, string | readonly string[] | undefined>>): string {
  return typeof query.data_referencia === "string" && /^\d{4}-\d{2}-\d{2}$/.test(query.data_referencia)
    ? query.data_referencia
    : new Date().toISOString().slice(0, 10);
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
  // O nome do Devedor e o titulo do painel: sem ele a pagina abriria sem dizer
  // de quem e o emprestimo. Falta de permissao degrada o titulo, nunca a pagina.
  const [installments, balance, memories, settlement, devedor] = loan.kind === "ready"
    ? await Promise.all([
      getInstallments(cookieStore, context, emprestimoId, dependencies),
      getBalance(cookieStore, context, emprestimoId, selectedDate, dependencies),
      getMemories(cookieStore, context, emprestimoId, dependencies),
      getSettlementPreview(cookieStore, context, emprestimoId, selectedDate, dependencies),
      getDevedor(cookieStore, context, loan.data.devedor_id, dependencies),
    ])
    : [
      denied<InstallmentPlan>(),
      denied<Balance>(),
      denied<readonly CalculationMemory[]>(),
      denied<SettlementPreview>(),
      denied<never>(),
    ];
  for (const result of [installments, balance, memories, settlement]) {
    if (result.kind === "problem" && result.problem.status === 401) redirect(recoveryHref);
  }
  return (
    <MotorDetailPage
      balance={balance}
      devedor={devedor.kind === "ready" && "nome" in devedor.data ? devedor.data.nome : undefined}
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
