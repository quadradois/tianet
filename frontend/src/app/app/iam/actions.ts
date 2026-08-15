"use server";

import { revalidatePath } from "next/cache";
import { cookies } from "next/headers";

import { createRuntimeDependencies } from "@/lib/bff/backend.server";
import {
  addPermissionToPerfil,
  assignPerfilToUsuario,
  createPerfil,
  inactivatePerfil,
  removePerfilFromUsuario,
  removePermissionFromPerfil,
  renamePerfil,
} from "@/lib/bff/iam.server";
import { currentOperationalContext } from "@/lib/bff/current-context.server";
import type { IamActionState } from "@/lib/iam/iam-policy";

async function run(
  action: (cookieStore: Awaited<ReturnType<typeof cookies>>, formData: FormData) => Promise<IamActionState>,
  formData: FormData,
) {
  const result = await action(await cookies(), formData);
  if (result.kind === "success") revalidatePath("/app/iam");
  return result;
}

export async function createPerfilAction(_state: IamActionState, formData: FormData): Promise<IamActionState> {
  return run(async (cookieStore, data) => createPerfil(cookieStore, await currentOperationalContext(), data, createRuntimeDependencies()), formData);
}

export async function renamePerfilAction(_state: IamActionState, formData: FormData): Promise<IamActionState> {
  return run(async (cookieStore, data) => renamePerfil(cookieStore, await currentOperationalContext(), data, createRuntimeDependencies()), formData);
}

export async function inactivatePerfilAction(_state: IamActionState, formData: FormData): Promise<IamActionState> {
  return run(async (cookieStore, data) => inactivatePerfil(cookieStore, await currentOperationalContext(), data, createRuntimeDependencies()), formData);
}

export async function addPermissionAction(_state: IamActionState, formData: FormData): Promise<IamActionState> {
  return run(async (cookieStore, data) => addPermissionToPerfil(cookieStore, await currentOperationalContext(), data, createRuntimeDependencies()), formData);
}

export async function removePermissionAction(_state: IamActionState, formData: FormData): Promise<IamActionState> {
  return run(async (cookieStore, data) => removePermissionFromPerfil(cookieStore, await currentOperationalContext(), data, createRuntimeDependencies()), formData);
}

export async function assignPerfilAction(_state: IamActionState, formData: FormData): Promise<IamActionState> {
  return run(async (cookieStore, data) => assignPerfilToUsuario(cookieStore, await currentOperationalContext(), data, createRuntimeDependencies()), formData);
}

export async function removePerfilUsuarioAction(_state: IamActionState, formData: FormData): Promise<IamActionState> {
  return run(async (cookieStore, data) => removePerfilFromUsuario(cookieStore, await currentOperationalContext(), data, createRuntimeDependencies()), formData);
}
