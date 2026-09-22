"use server";

import { revalidatePath } from "next/cache";
import { cookies } from "next/headers";

import { createRuntimeDependencies } from "@/lib/bff/backend.server";
import { currentOperationalContext } from "@/lib/bff/current-context.server";
import {
  disableMercadoPago,
  enableMercadoPago,
  saveChavePix,
  saveMercadoPagoCredentials,
  testMercadoPagoCredentials,
} from "@/lib/bff/mercadopago.server";
import type { ChavePixActionState, MercadoPagoActionState } from "@/lib/pagamentos/mercadopago-policy";

/**
 * Uma acao so, escolhida por `intent` — pelo mesmo motivo do WhatsApp: com
 * `useActionState` separados, o resultado de "ligar" sobreviveria ao
 * "desligar" e a tela mostraria a mensagem da operacao anterior.
 */
export async function mercadoPagoAction(
  _state: MercadoPagoActionState,
  formData: FormData,
): Promise<MercadoPagoActionState> {
  const dependencies = createRuntimeDependencies();
  const context = await currentOperationalContext();
  const cookieStore = await cookies();
  const intent = formData.get("intent");

  const result =
    intent === "testar"
      ? await testMercadoPagoCredentials(cookieStore, context, dependencies, formData)
      : intent === "habilitar"
        ? await enableMercadoPago(cookieStore, context, dependencies, formData)
        : intent === "desabilitar"
          ? await disableMercadoPago(cookieStore, context, dependencies, formData)
          : await saveMercadoPagoCredentials(cookieStore, context, dependencies, formData);

  if (result.kind === "success") revalidatePath("/app/pagamentos");
  return result;
}


/** Grava a chave Pix da Credora — o caminho sem taxa. */
export async function chavePixAction(
  _state: ChavePixActionState,
  formData: FormData,
): Promise<ChavePixActionState> {
  const result = await saveChavePix(
    await cookies(),
    await currentOperationalContext(),
    createRuntimeDependencies(),
    formData,
  );
  if (result.kind === "success") revalidatePath("/app/pagamentos");
  return result;
}
