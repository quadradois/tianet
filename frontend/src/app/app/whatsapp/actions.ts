"use server";

import { revalidatePath } from "next/cache";
import { cookies } from "next/headers";

import { createRuntimeDependencies } from "@/lib/bff/backend.server";
import { currentOperationalContext } from "@/lib/bff/current-context.server";
import { connectWhatsApp, disconnectWhatsApp } from "@/lib/bff/whatsapp.server";
import type { WhatsAppActionState } from "@/lib/whatsapp/whatsapp-policy";

/**
 * Uma acao so para conectar e desconectar, escolhida por `intent`.
 *
 * **Nao e economia de linhas, e correcao.** Com dois `useActionState`
 * independentes, o resultado do "conectar" — que carrega o QR — sobrevivia ao
 * "desconectar", e o codigo antigo reaparecia na tela depois do logout (achado do
 * review do IMP-369). Com uma acao so, o estado exibido e sempre o da ULTIMA
 * operacao: desconectar substitui o resultado anterior, e o QR some sem nenhum
 * efeito colateral para limpa-lo.
 *
 * `revalidatePath` roda tambem no sucesso porque o selo da barra lateral le o
 * contexto operacional — sem revalidar, ele so mudaria na proxima navegacao.
 */
export async function whatsappAction(_state: WhatsAppActionState, formData: FormData): Promise<WhatsAppActionState> {
  const desconectar = formData.get("intent") === "desconectar";
  const dependencies = createRuntimeDependencies();
  const context = await currentOperationalContext();
  const cookieStore = await cookies();

  const result = desconectar
    ? await disconnectWhatsApp(cookieStore, context, dependencies)
    : await connectWhatsApp(cookieStore, context, dependencies);

  // Revalida tambem quando CONECTAR falha: o `POST` pode ter criado a instancia
  // antes de o QR falhar, e a tela precisa refletir a instancia que passou a
  // existir. No desconectar, falha nao muda estado local.
  if (result.kind === "success" || !desconectar) revalidatePath("/app/whatsapp");
  return result;
}
