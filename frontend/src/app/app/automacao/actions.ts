"use server";

import { revalidatePath } from "next/cache";
import { cookies } from "next/headers";

import {
  activateTemplate,
  approveTemplate,
  cancelJob,
  createTemplate,
  reconcileNotification,
  retryJob,
} from "@/lib/bff/automacao.server";
import { createRuntimeDependencies } from "@/lib/bff/backend.server";
import { currentOperationalContext } from "@/lib/bff/current-context.server";
import type { AutomacaoActionState } from "@/lib/automacao/automacao-policy";

async function run(
  action: (cookieStore: Awaited<ReturnType<typeof cookies>>, formData: FormData) => Promise<AutomacaoActionState>,
  formData: FormData,
) {
  const result = await action(await cookies(), formData);
  if (result.kind === "success") revalidatePath("/app/automacao");
  return result;
}

export async function cancelJobAction(_state: AutomacaoActionState, formData: FormData): Promise<AutomacaoActionState> {
  return run(async (cookieStore, data) => cancelJob(cookieStore, await currentOperationalContext(), data, createRuntimeDependencies()), formData);
}

export async function retryJobAction(_state: AutomacaoActionState, formData: FormData): Promise<AutomacaoActionState> {
  return run(async (cookieStore, data) => retryJob(cookieStore, await currentOperationalContext(), data, createRuntimeDependencies()), formData);
}

export async function createTemplateAction(_state: AutomacaoActionState, formData: FormData): Promise<AutomacaoActionState> {
  return run(async (cookieStore, data) => createTemplate(cookieStore, await currentOperationalContext(), data, createRuntimeDependencies()), formData);
}

export async function approveTemplateAction(_state: AutomacaoActionState, formData: FormData): Promise<AutomacaoActionState> {
  return run(async (cookieStore, data) => approveTemplate(cookieStore, await currentOperationalContext(), data, createRuntimeDependencies()), formData);
}

export async function activateTemplateAction(_state: AutomacaoActionState, formData: FormData): Promise<AutomacaoActionState> {
  return run(async (cookieStore, data) => activateTemplate(cookieStore, await currentOperationalContext(), data, createRuntimeDependencies()), formData);
}

export async function reconcileNotificationAction(_state: AutomacaoActionState, formData: FormData): Promise<AutomacaoActionState> {
  return run(async (cookieStore, data) => reconcileNotification(cookieStore, await currentOperationalContext(), data, createRuntimeDependencies()), formData);
}
