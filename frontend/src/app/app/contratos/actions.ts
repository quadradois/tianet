"use server";

import { revalidatePath } from "next/cache";
import { cookies } from "next/headers";

import { createRuntimeDependencies } from "@/lib/bff/backend.server";
import { currentOperationalContext } from "@/lib/bff/current-context.server";
import { createContract, decideContract } from "@/lib/bff/contratos.server";
import { CONTRACT_DECISIONS, type ContratoActionState } from "@/lib/contratos/contratos-policy";

function contratoPath(contratoId: string): string {
  return `/app/contratos/${contratoId}`;
}

export async function createContractAction(_state: ContratoActionState, formData: FormData): Promise<ContratoActionState> {
  const result = await createContract(await cookies(), await currentOperationalContext(), formData, createRuntimeDependencies());
  if (result.kind === "success") revalidatePath("/app/contratos");
  return result;
}

export async function decideContractAction(_state: ContratoActionState, formData: FormData): Promise<ContratoActionState> {
  const contratoId = formData.get("contrato_id");
  const decision = formData.get("decision");
  const target = typeof contratoId === "string" ? contratoId : "";
  const selected = CONTRACT_DECISIONS.find((value) => value === decision);
  if (!selected) return { kind: "problem", message: "Decisao contratual invalida.", status: 400 };
  const result = await decideContract(await cookies(), await currentOperationalContext(), target, selected, formData, createRuntimeDependencies());
  if (result.kind === "success") {
    revalidatePath("/app/contratos");
    revalidatePath(contratoPath(target));
  }
  return result;
}
