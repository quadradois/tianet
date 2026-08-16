"use server";

import { revalidatePath } from "next/cache";
import { cookies } from "next/headers";

import { createRuntimeDependencies } from "@/lib/bff/backend.server";
import {
  activateConfiguracao,
  approveConfiguracao,
  captureSnapshot,
  createCalendario,
  createConfiguracao,
  createModalidade,
  inactivateConfiguracao,
  programConfiguracao,
} from "@/lib/bff/configuracoes-financeiras.server";
import { currentOperationalContext } from "@/lib/bff/current-context.server";
import type { ConfiguracoesActionState } from "@/lib/configuracoes-financeiras/configuracoes-policy";

async function run(action: (cookieStore: Awaited<ReturnType<typeof cookies>>, formData: FormData) => Promise<ConfiguracoesActionState>, formData: FormData) {
  const result = await action(await cookies(), formData);
  if (result.kind === "success") revalidatePath("/app/configuracoes-financeiras");
  return result;
}

export async function createModalidadeAction(_state: ConfiguracoesActionState, formData: FormData): Promise<ConfiguracoesActionState> {
  return run(async (cookieStore, data) => createModalidade(cookieStore, await currentOperationalContext(), data, createRuntimeDependencies()), formData);
}

export async function createCalendarioAction(_state: ConfiguracoesActionState, formData: FormData): Promise<ConfiguracoesActionState> {
  return run(async (cookieStore, data) => createCalendario(cookieStore, await currentOperationalContext(), data, createRuntimeDependencies()), formData);
}

export async function createConfiguracaoAction(_state: ConfiguracoesActionState, formData: FormData): Promise<ConfiguracoesActionState> {
  return run(async (cookieStore, data) => createConfiguracao(cookieStore, await currentOperationalContext(), data, createRuntimeDependencies()), formData);
}

export async function approveConfiguracaoAction(_state: ConfiguracoesActionState, formData: FormData): Promise<ConfiguracoesActionState> {
  return run(async (cookieStore, data) => approveConfiguracao(cookieStore, await currentOperationalContext(), data, createRuntimeDependencies()), formData);
}

export async function programConfiguracaoAction(_state: ConfiguracoesActionState, formData: FormData): Promise<ConfiguracoesActionState> {
  return run(async (cookieStore, data) => programConfiguracao(cookieStore, await currentOperationalContext(), data, createRuntimeDependencies()), formData);
}

export async function activateConfiguracaoAction(_state: ConfiguracoesActionState, formData: FormData): Promise<ConfiguracoesActionState> {
  return run(async (cookieStore, data) => activateConfiguracao(cookieStore, await currentOperationalContext(), data, createRuntimeDependencies()), formData);
}

export async function inactivateConfiguracaoAction(_state: ConfiguracoesActionState, formData: FormData): Promise<ConfiguracoesActionState> {
  return run(async (cookieStore, data) => inactivateConfiguracao(cookieStore, await currentOperationalContext(), data, createRuntimeDependencies()), formData);
}

export async function captureSnapshotAction(_state: ConfiguracoesActionState, formData: FormData): Promise<ConfiguracoesActionState> {
  return run(async (cookieStore, data) => captureSnapshot(cookieStore, await currentOperationalContext(), data, createRuntimeDependencies()), formData);
}
