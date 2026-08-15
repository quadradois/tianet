"use server";

import { revalidatePath } from "next/cache";
import { cookies } from "next/headers";

import { createRuntimeDependencies } from "@/lib/bff/backend.server";
import { currentOperationalContext } from "@/lib/bff/current-context.server";
import {
  createCommercialProposal,
  createCommercialSimulation,
  decideCommercialProposal,
  updateCommercialProposal,
} from "@/lib/bff/comercial.server";
import type { ComercialActionState } from "@/lib/comercial/comercial-policy";

function devedorPath(devedorId: string): string {
  return `/app/devedores/${devedorId}/comercial`;
}

function propostaPath(propostaId: string): string {
  return `/app/comercial/propostas/${propostaId}`;
}

export async function createSimulationAction(_state: ComercialActionState, formData: FormData): Promise<ComercialActionState> {
  const devedorId = formData.get("devedor_id");
  const target = typeof devedorId === "string" ? devedorId : "";
  const result = await createCommercialSimulation(await cookies(), await currentOperationalContext(), target, formData, createRuntimeDependencies());
  if (result.kind === "success") revalidatePath(devedorPath(target));
  return result;
}

export async function createProposalAction(_state: ComercialActionState, formData: FormData): Promise<ComercialActionState> {
  const devedorId = formData.get("devedor_id");
  const target = typeof devedorId === "string" ? devedorId : "";
  const result = await createCommercialProposal(await cookies(), await currentOperationalContext(), target, formData, createRuntimeDependencies());
  if (result.kind === "success") revalidatePath(devedorPath(target));
  return result;
}

export async function updateProposalAction(_state: ComercialActionState, formData: FormData): Promise<ComercialActionState> {
  const propostaId = formData.get("proposta_id");
  const target = typeof propostaId === "string" ? propostaId : "";
  const result = await updateCommercialProposal(await cookies(), await currentOperationalContext(), target, formData, createRuntimeDependencies());
  if (result.kind === "success") revalidatePath(propostaPath(target));
  return result;
}

export async function decideProposalAction(_state: ComercialActionState, formData: FormData): Promise<ComercialActionState> {
  const propostaId = formData.get("proposta_id");
  const decision = formData.get("decision");
  const target = typeof propostaId === "string" ? propostaId : "";
  const allowed = ["enviar-para-analise", "aprovar", "recusar", "cancelar", "expirar"] as const;
  const selected = allowed.find((value) => value === decision);
  if (!selected) return { kind: "problem", message: "Decisao comercial invalida.", status: 400 };
  const result = await decideCommercialProposal(await cookies(), await currentOperationalContext(), target, selected, formData, createRuntimeDependencies());
  if (result.kind === "success") revalidatePath(propostaPath(target));
  return result;
}
