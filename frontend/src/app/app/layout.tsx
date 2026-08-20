import type { Metadata } from "next";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import type { ReactNode } from "react";

import { AppShell } from "@/components/shell/app-shell";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiProblem, createRuntimeDependencies } from "@/lib/bff/backend.server";
import { recoveryAttemptCookieName } from "@/lib/bff/context.server";
import { currentOperationalContext } from "@/lib/bff/current-context.server";

export const metadata: Metadata = {
  title: "Dashboard | TiaNet",
};

type AuthenticatedLayoutProps = Readonly<{ children: ReactNode }>;
type ContextResult =
  | Readonly<{ context: Awaited<ReturnType<typeof currentOperationalContext>>; problem?: never }>
  | Readonly<{ context?: never; problem: ApiProblem }>;

function ContextFailure({ problem }: Readonly<{ problem: ApiProblem }>) {
  const conflict = problem.status === 409;
  return (
    <main className="grid min-h-screen place-items-center px-5 py-10" id="conteudo-principal" tabIndex={-1}>
      <Card className="w-full max-w-xl">
        <CardHeader>
          <CardTitle>{conflict ? "Contexto operacional indisponivel" : "Servico temporariamente indisponivel"}</CardTitle>
          <CardDescription>
            {conflict
              ? "Nenhuma Carteira alternativa foi escolhida. Solicite a regularizacao do seu contexto operacional."
              : "Tente novamente mais tarde. O identificador abaixo ajuda no atendimento."}
          </CardDescription>
        </CardHeader>
        <CardContent><p className="text-sm text-muted-foreground">Correlation ID: {problem.correlationId}</p></CardContent>
      </Card>
    </main>
  );
}

export default async function AuthenticatedLayout({ children }: AuthenticatedLayoutProps) {
  const cookieStore = await cookies();
  const dependencies = createRuntimeDependencies();
  let result: ContextResult;
  try {
    result = { context: await currentOperationalContext() };
  } catch (error) {
    if (error instanceof ApiProblem && error.status === 401) {
      redirect(cookieStore.get(recoveryAttemptCookieName(dependencies.config)) ? "/login" : "/session/recover");
    }
    result = { problem: error instanceof ApiProblem
      ? error
      : new ApiProblem({ status: 500, codigo: "erro_tecnico", mensagem: "Servico temporariamente indisponivel.", correlationId: "indisponivel" }) };
  }
  return result.problem
    ? <ContextFailure problem={result.problem} />
    : <AppShell context={result.context}>{children}</AppShell>;
}
