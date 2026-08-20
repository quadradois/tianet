import type { Metadata } from "next";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { Relatorios } from "@/components/relatorios/relatorios";
import { ApiProblem, createRuntimeDependencies } from "@/lib/bff/backend.server";
import { recoveryAttemptCookieName } from "@/lib/bff/context.server";
import { currentOperationalContext } from "@/lib/bff/current-context.server";
import { beginReportsLoads } from "@/lib/bff/relatorios.server";
import { resolveReportsPeriod } from "@/lib/relatorios/relatorios-policy";

export const metadata: Metadata = {
  title: "Relatorios | TiaNet",
};

export default async function RelatoriosPage({ searchParams }: PageProps<"/app/relatorios">) {
  const query = await searchParams;
  const periodState = resolveReportsPeriod(query);
  const cookieStore = await cookies();
  const dependencies = createRuntimeDependencies();
  const recoveryHref = cookieStore.get(recoveryAttemptCookieName(dependencies.config)) ? "/login" : "/session/recover";
  if (periodState.kind !== "ready") return <Relatorios periodState={periodState} recoveryHref={recoveryHref} />;
  const context = await currentOperationalContext();
  let loads: Awaited<ReturnType<typeof beginReportsLoads>>;
  try {
    loads = await beginReportsLoads(cookieStore, context, periodState.period, dependencies);
  } catch (error) {
    if (error instanceof ApiProblem && error.status === 401) redirect(recoveryHref);
    throw error;
  }
  return <Relatorios {...loads} periodState={periodState} recoveryHref={recoveryHref} />;
}
