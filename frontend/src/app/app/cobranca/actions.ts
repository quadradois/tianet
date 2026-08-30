"use server";

import { revalidatePath } from "next/cache";
import { cookies } from "next/headers";

import { createRuntimeDependencies } from "@/lib/bff/backend.server";
import { currentOperationalContext } from "@/lib/bff/current-context.server";
import {
  appropriatePaymentPromise,
  registerCollectionAction,
  registerPaymentPromise,
} from "@/lib/bff/cobranca.server";
import type { CobrancaActionState } from "@/lib/cobranca/cobranca-policy";

export async function registerCollectionActionAction(_state: CobrancaActionState, formData: FormData): Promise<CobrancaActionState> {
  const result = await registerCollectionAction(await cookies(), await currentOperationalContext(), formData, createRuntimeDependencies());
  if (result.kind === "success") revalidatePath("/app/cobranca");
  return result;
}

export async function registerPromiseAction(_state: CobrancaActionState, formData: FormData): Promise<CobrancaActionState> {
  const result = await registerPaymentPromise(await cookies(), await currentOperationalContext(), formData, createRuntimeDependencies());
  if (result.kind === "success") revalidatePath("/app/cobranca");
  return result;
}

export async function appropriatePromiseAction(_state: CobrancaActionState, formData: FormData): Promise<CobrancaActionState> {
  const result = await appropriatePaymentPromise(await cookies(), await currentOperationalContext(), formData, createRuntimeDependencies());
  if (result.kind === "success") revalidatePath("/app/cobranca");
  return result;
}
