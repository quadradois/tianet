"use server";

import { revalidatePath } from "next/cache";
import { cookies } from "next/headers";

import { correlationId, createRuntimeDependencies } from "@/lib/bff/backend.server";
import { currentOperationalContext } from "@/lib/bff/current-context.server";
import { beginOpenAILogin, disconnectOpenAI, refreshOpenAIDiagnostic } from "@/lib/bff/openai.server";
import { validatedChallengeFromActionState, type OpenAIActionState } from "@/lib/openai/openai-policy";

export async function openAIAction(state: OpenAIActionState, formData: FormData): Promise<OpenAIActionState> {
  const intent = String(formData.get("intent") ?? "");
  if (!new Set(["conectar", "desconectar", "diagnostico"]).has(intent)) {
    return { kind: "problem", message: "Operação OpenAI inválida.", status: 400, correlationId: correlationId() };
  }
  const dependencies = createRuntimeDependencies();
  const context = await currentOperationalContext();
  const cookieStore = await cookies();
  const result = intent === "diagnostico"
    ? await refreshOpenAIDiagnostic(cookieStore, context, dependencies)
    : intent === "desconectar"
      ? await disconnectOpenAI(cookieStore, context, dependencies)
      : await beginOpenAILogin(cookieStore, context, dependencies);
  if (result.kind === "login" || result.kind === "logout" || result.kind === "diagnostic") {
    revalidatePath("/app/openai");
  }
  const previousChallenge = validatedChallengeFromActionState(state);
  if (previousChallenge && (result.kind === "diagnostic" || result.kind === "problem")) {
    return { ...result, challenge: previousChallenge };
  }
  return result;
}
