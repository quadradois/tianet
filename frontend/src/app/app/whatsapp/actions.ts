"use server";

import { revalidatePath } from "next/cache";
import { cookies } from "next/headers";

import { createRuntimeDependencies } from "@/lib/bff/backend.server";
import { currentOperationalContext } from "@/lib/bff/current-context.server";
import { connectWhatsApp, disconnectWhatsApp } from "@/lib/bff/whatsapp.server";
import type { WhatsAppActionState } from "@/lib/whatsapp/whatsapp-policy";

/**
 * Gera o QR de AGORA.
 *
 * Repetir e o uso normal, nao excecao: o QR expira em ~20 segundos e o provedor
 * o rotaciona sozinho. Cada clique traz o atual sobre a MESMA instancia.
 *
 * `revalidatePath` roda tambem no caminho de sucesso porque o selo da barra
 * lateral le o contexto operacional — sem revalidar, ele so mudaria na proxima
 * navegacao.
 *
 * Sem parametros de proposito: `useActionState` chama com `(state, formData)` e
 * estas acoes nao precisam de nenhum dos dois — o `POST` da conexao nao tem
 * corpo (o nome da instancia e derivado do Tenant, IMP-368). Declarar e ignorar
 * so criaria parametro morto.
 */
export async function connectWhatsAppAction(): Promise<WhatsAppActionState> {
  const result = await connectWhatsApp(await cookies(), await currentOperationalContext(), createRuntimeDependencies());
  revalidatePath("/app/whatsapp");
  return result;
}

export async function disconnectWhatsAppAction(): Promise<WhatsAppActionState> {
  const result = await disconnectWhatsApp(await cookies(), await currentOperationalContext(), createRuntimeDependencies());
  if (result.kind === "success") revalidatePath("/app/whatsapp");
  return result;
}
