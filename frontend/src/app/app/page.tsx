import type { Metadata } from "next";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { Dashboard, InvalidPeriodState } from "@/components/dashboard/dashboard";
import { ApiProblem, createRuntimeDependencies } from "@/lib/bff/backend.server";
import { recoveryAttemptCookieName } from "@/lib/bff/context.server";
import { currentOperationalContext } from "@/lib/bff/current-context.server";
import { beginDashboardLoads } from "@/lib/bff/dashboard.server";
import { resolveDashboardPeriod } from "@/lib/dashboard/dashboard-policy";

export const metadata: Metadata = {
  title: "Dashboard | TiaNet",
};

export default async function AppHomePage({ searchParams }: PageProps<"/app">) {
  const query = await searchParams;
  const decision = resolveDashboardPeriod(query.data_referencia);
  if (decision.kind === "canonical") redirect(`/app?data_referencia=${decision.referenceDate}`);
  if (decision.kind === "invalid") {
    return <div className="grid gap-5"><h1 className="text-3xl font-bold tracking-tight">Inicio</h1><InvalidPeriodState /></div>;
  }
  const cookieStore = await cookies();
  const dependencies = createRuntimeDependencies();
  const context = await currentOperationalContext();
  let loads;
  try {
    loads = await beginDashboardLoads(cookieStore, context, decision.period, dependencies);
  } catch (error) {
    if (error instanceof ApiProblem && error.status === 401) {
      redirect(cookieStore.get(recoveryAttemptCookieName(dependencies.config)) ? "/login" : "/session/recover");
    }
    throw error;
  }
  return <Dashboard {...loads} period={decision.period} recoveryHref={cookieStore.get(recoveryAttemptCookieName(dependencies.config)) ? "/login" : "/session/recover"} />;
}
