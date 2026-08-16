"use server";

import { cookies } from "next/headers";
import { revalidatePath } from "next/cache";

import { createRuntimeDependencies } from "@/lib/bff/backend.server";
import { currentOperationalContext } from "@/lib/bff/current-context.server";
import {
  createDevedor,
  inactivateDevedor,
  reactivateDevedor,
  updateDevedor,
} from "@/lib/bff/devedores.server";
import type { DevedorActionState } from "@/lib/devedores/devedores-policy";

export async function createDevedorAction(_state: DevedorActionState, formData: FormData): Promise<DevedorActionState> {
  const result = await createDevedor(await cookies(), await currentOperationalContext(), formData, createRuntimeDependencies());
  if (result.kind === "success") revalidatePath("/app/devedores");
  return result;
}

export async function updateDevedorAction(_state: DevedorActionState, formData: FormData): Promise<DevedorActionState> {
  const devedorId = formData.get("devedor_id");
  const result = await updateDevedor(
    await cookies(),
    await currentOperationalContext(),
    typeof devedorId === "string" ? devedorId : "",
    formData,
    createRuntimeDependencies(),
  );
  if (result.kind === "success") revalidatePath(`/app/devedores/${devedorId}`);
  return result;
}

export async function inactivateDevedorAction(_state: DevedorActionState, formData: FormData): Promise<DevedorActionState> {
  const devedorId = formData.get("devedor_id");
  const result = await inactivateDevedor(
    await cookies(),
    await currentOperationalContext(),
    typeof devedorId === "string" ? devedorId : "",
    createRuntimeDependencies(),
  );
  if (result.kind === "success") revalidatePath(`/app/devedores/${devedorId}`);
  return result;
}

export async function reactivateDevedorAction(_state: DevedorActionState, formData: FormData): Promise<DevedorActionState> {
  const devedorId = formData.get("devedor_id");
  const result = await reactivateDevedor(
    await cookies(),
    await currentOperationalContext(),
    typeof devedorId === "string" ? devedorId : "",
    createRuntimeDependencies(),
  );
  if (result.kind === "success") revalidatePath(`/app/devedores/${devedorId}`);
  return result;
}
