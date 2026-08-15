import type { Metadata } from "next";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { IamAdmin } from "@/components/iam/iam-admin";
import { ApiProblem, createRuntimeDependencies } from "@/lib/bff/backend.server";
import { recoveryAttemptCookieName } from "@/lib/bff/context.server";
import { currentOperationalContext } from "@/lib/bff/current-context.server";
import { beginIamLoads } from "@/lib/bff/iam.server";
import { resolveIamFilters } from "@/lib/iam/iam-policy";

import {
  addPermissionAction,
  assignPerfilAction,
  createPerfilAction,
  inactivatePerfilAction,
  removePerfilUsuarioAction,
  removePermissionAction,
  renamePerfilAction,
} from "./actions";

export const metadata: Metadata = {
  title: "IAM permitido | Frontend MVP",
};

export default async function IamPage({ searchParams }: PageProps<"/app/iam">) {
  const filters = resolveIamFilters(await searchParams);
  const cookieStore = await cookies();
  const dependencies = createRuntimeDependencies();
  const recoveryHref = cookieStore.get(recoveryAttemptCookieName(dependencies.config)) ? "/login" : "/session/recover";
  const context = await currentOperationalContext();
  let loads: Awaited<ReturnType<typeof beginIamLoads>>;
  try {
    loads = await beginIamLoads(cookieStore, context, filters, dependencies);
  } catch (error) {
    if (error instanceof ApiProblem && error.status === 401) redirect(recoveryHref);
    throw error;
  }
  return (
    <IamAdmin
      actions={{
        addPermissionAction,
        assignPerfilAction,
        createPerfilAction,
        inactivatePerfilAction,
        removePerfilUsuarioAction,
        removePermissionAction,
        renamePerfilAction,
      }}
      filters={filters}
      permissions={context.permissoes}
      recoveryHref={recoveryHref}
      {...loads}
    />
  );
}
