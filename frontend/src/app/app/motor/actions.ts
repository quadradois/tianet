"use server";

import { revalidatePath } from "next/cache";
import { cookies } from "next/headers";

import { createRuntimeDependencies } from "@/lib/bff/backend.server";
import { currentOperationalContext } from "@/lib/bff/current-context.server";
import {
  createLoanFromContract,
  executeSettlement,
  registerPayment,
  registerRenegotiation,
} from "@/lib/bff/motor.server";
import { type MotorActionState } from "@/lib/motor/motor-policy";

function loanPath(loanId: string): string {
  return `/app/motor/${loanId}`;
}

export async function createLoanAction(_state: MotorActionState, formData: FormData): Promise<MotorActionState> {
  const result = await createLoanFromContract(await cookies(), await currentOperationalContext(), formData, createRuntimeDependencies());
  if (result.kind === "success") {
    revalidatePath("/app/motor");
    if (result.targetId) revalidatePath(loanPath(result.targetId));
  }
  return result;
}


export async function registerPaymentAction(_state: MotorActionState, formData: FormData): Promise<MotorActionState> {
  const loanId = formData.get("emprestimo_id");
  const target = typeof loanId === "string" ? loanId : "";
  const result = await registerPayment(await cookies(), await currentOperationalContext(), target, formData, createRuntimeDependencies());
  if (result.kind === "success") revalidatePath(loanPath(target));
  return result;
}

export async function executeSettlementAction(_state: MotorActionState, formData: FormData): Promise<MotorActionState> {
  const loanId = formData.get("emprestimo_id");
  const target = typeof loanId === "string" ? loanId : "";
  const result = await executeSettlement(await cookies(), await currentOperationalContext(), target, formData, createRuntimeDependencies());
  if (result.kind === "success") {
    revalidatePath("/app/motor");
    revalidatePath(loanPath(target));
  }
  return result;
}

export async function registerRenegotiationAction(_state: MotorActionState, formData: FormData): Promise<MotorActionState> {
  const loanId = formData.get("emprestimo_id");
  const target = typeof loanId === "string" ? loanId : "";
  const result = await registerRenegotiation(await cookies(), await currentOperationalContext(), target, formData, createRuntimeDependencies());
  if (result.kind === "success") revalidatePath(loanPath(target));
  return result;
}

export async function motorCommandAction(state: MotorActionState, formData: FormData): Promise<MotorActionState> {
  const command = formData.get("command");
  if (command === "registrar-pagamento") return registerPaymentAction(state, formData);
  if (command === "executar-quitacao") return executeSettlementAction(state, formData);
  if (command === "registrar-renegociacao") return registerRenegotiationAction(state, formData);
  return { kind: "problem", message: "Comando do Motor invalido.", status: 400 };
}
