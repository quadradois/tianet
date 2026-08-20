import type { Metadata } from "next";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { DevedorDetailPage } from "@/components/devedores/devedores";
import { EmprestimosDoDevedor } from "@/components/motor/motor";
import { createRuntimeDependencies } from "@/lib/bff/backend.server";
import { recoveryAttemptCookieName } from "@/lib/bff/context.server";
import { currentOperationalContext } from "@/lib/bff/current-context.server";
import { getDevedor, getDevedorHistory } from "@/lib/bff/devedores.server";
import { listLoans } from "@/lib/bff/motor.server";
import { INITIAL_DEVEDOR_ACTION_STATE } from "@/lib/devedores/devedores-policy";

import {
  inactivateDevedorAction,
  reactivateDevedorAction,
  updateDevedorAction,
} from "../actions";

export const metadata: Metadata = {
  title: "Detalhe do Devedor | TiaNet",
};

export default async function DevedorDetailRoute({ params }: PageProps<"/app/devedores/[devedorId]">) {
  const { devedorId } = await params;
  const cookieStore = await cookies();
  const dependencies = createRuntimeDependencies();
  const context = await currentOperationalContext();
  const [devedor, history, emprestimos] = await Promise.all([
    getDevedor(cookieStore, context, devedorId, dependencies),
    getDevedorHistory(cookieStore, context, devedorId, dependencies),
    // Filtro por Devedor que o endpoint de listagem ja aceita: nenhuma
    // superficie nova, e a situacao vem do backend em vez de ser deduzida aqui.
    listLoans(cookieStore, context, { devedorId, page: 1, size: 100 }, dependencies),
  ]);
  const recoveryHref = cookieStore.get(recoveryAttemptCookieName(dependencies.config)) ? "/login" : "/session/recover";
  for (const result of [devedor, history, emprestimos]) {
    if (result.kind === "problem" && result.problem.status === 401) redirect(recoveryHref);
  }
  return (
    <>
      {/* Os emprestimos vem antes de editar cadastro, inativar e historico: o
          Credor pediu que abrir um devedor ja mostrasse a situacao dele. No
          IMP-310 este bloco ficou no rodape, o que cumpria o criterio do
          backlog e nao a intencao do pedido. */}
      <div className="p-6 pb-0">
        <EmprestimosDoDevedor recoveryHref={recoveryHref} result={emprestimos} />
      </div>
      <DevedorDetailPage
        devedor={devedor}
        history={history}
        inactivateAction={inactivateDevedorAction}
        initialState={INITIAL_DEVEDOR_ACTION_STATE}
        permissions={context.permissoes}
        reactivateAction={reactivateDevedorAction}
        recoveryHref={recoveryHref}
        updateAction={updateDevedorAction}
      />
    </>
  );
}
