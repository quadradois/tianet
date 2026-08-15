import type { Metadata } from "next";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { DevedorDetailPage } from "@/components/devedores/devedores";
import { createRuntimeDependencies } from "@/lib/bff/backend.server";
import { recoveryAttemptCookieName } from "@/lib/bff/context.server";
import { currentOperationalContext } from "@/lib/bff/current-context.server";
import { getDevedor, getDevedorHistory } from "@/lib/bff/devedores.server";
import { INITIAL_DEVEDOR_ACTION_STATE } from "@/lib/devedores/devedores-policy";

import {
  inactivateDevedorAction,
  reactivateDevedorAction,
  updateDevedorAction,
} from "../actions";

export const metadata: Metadata = {
  title: "Detalhe do Devedor | Frontend MVP",
};

export default async function DevedorDetailRoute({ params }: PageProps<"/app/devedores/[devedorId]">) {
  const { devedorId } = await params;
  const cookieStore = await cookies();
  const dependencies = createRuntimeDependencies();
  const context = await currentOperationalContext();
  const [devedor, history] = await Promise.all([
    getDevedor(cookieStore, context, devedorId, dependencies),
    getDevedorHistory(cookieStore, context, devedorId, dependencies),
  ]);
  for (const result of [devedor, history]) {
    if (result.kind === "problem" && result.problem.status === 401) {
      redirect(cookieStore.get(recoveryAttemptCookieName(dependencies.config)) ? "/login" : "/session/recover");
    }
  }
  return (
    <DevedorDetailPage
      devedor={devedor}
      history={history}
      inactivateAction={inactivateDevedorAction}
      initialState={INITIAL_DEVEDOR_ACTION_STATE}
      permissions={context.permissoes}
      reactivateAction={reactivateDevedorAction}
      recoveryHref={cookieStore.get(recoveryAttemptCookieName(dependencies.config)) ? "/login" : "/session/recover"}
      updateAction={updateDevedorAction}
    />
  );
}
