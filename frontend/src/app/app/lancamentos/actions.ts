"use server";

import { revalidatePath } from "next/cache";
import { cookies } from "next/headers";

import { createRuntimeDependencies } from "@/lib/bff/backend.server";
import { currentOperationalContext } from "@/lib/bff/current-context.server";
import { criarLancamento } from "@/lib/bff/lancamento.server";
import type { LancamentoActionState } from "@/lib/lancamento/lancamento-policy";

export async function lancarEmprestimoAction(
  _state: LancamentoActionState,
  formData: FormData,
): Promise<LancamentoActionState> {
  const resultado = await criarLancamento(
    await cookies(),
    await currentOperationalContext(),
    formData,
    createRuntimeDependencies(),
  );
  if (resultado.kind === "success") {
    revalidatePath("/app/motor");
    revalidatePath("/app/devedores");
  }
  return resultado;
}
