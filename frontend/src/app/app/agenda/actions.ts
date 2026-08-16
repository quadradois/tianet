"use server";

import { revalidatePath } from "next/cache";
import { cookies } from "next/headers";

import { agendaCommand } from "@/lib/bff/agenda-comunicacao.server";
import { createRuntimeDependencies } from "@/lib/bff/backend.server";
import { currentOperationalContext } from "@/lib/bff/current-context.server";
import type { AgendaActionState } from "@/lib/agenda/agenda-policy";

export async function agendaCommandAction(_state: AgendaActionState, formData: FormData): Promise<AgendaActionState> {
  const result = await agendaCommand(await cookies(), await currentOperationalContext(), formData, createRuntimeDependencies());
  if (result.kind === "success") revalidatePath("/app/agenda");
  return result;
}
