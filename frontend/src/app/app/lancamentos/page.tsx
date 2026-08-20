import type { Metadata } from "next";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import {
  LancamentoWizard,
  type DevedorResumo,
} from "@/components/lancamento/lancamento-wizard.client";
import { ApiProblem, createRuntimeDependencies } from "@/lib/bff/backend.server";
import { recoveryAttemptCookieName } from "@/lib/bff/context.server";
import { currentOperationalContext } from "@/lib/bff/current-context.server";
import { listDevedores } from "@/lib/bff/devedores.server";
import { resolveDevedoresFilters } from "@/lib/devedores/devedores-policy";
import {
  INITIAL_LANCAMENTO_ACTION_STATE,
  permissoesFaltantes,
  podeLancar,
} from "@/lib/lancamento/lancamento-policy";

import { lancarEmprestimoAction } from "./actions";

export const metadata: Metadata = {
  title: "Novo emprestimo | Frontend MVP",
};

export default async function LancamentosRoute() {
  const cookieStore = await cookies();
  const dependencies = createRuntimeDependencies();
  const destinoRecuperacao = cookieStore.get(recoveryAttemptCookieName(dependencies.config))
    ? "/login"
    : "/session/recover";

  // O layout guarda a propria chamada, mas layout e page renderizam
  // concorrentemente: a rejeicao daqui escapa antes do redirect do layout
  // abortar o render, e vira erro de Server Component no navegador.
  let context;
  try {
    context = await currentOperationalContext();
  } catch (error) {
    if (error instanceof ApiProblem && error.status === 401) redirect(destinoRecuperacao);
    throw error;
  }

  if (!podeLancar(context.permissoes)) {
    return (
      <main className="grid gap-2 p-6" id="conteudo-principal">
        <h1 className="text-2xl font-semibold">Novo emprestimo</h1>
        <p>Sem permissao</p>
        <p className="text-sm text-muted-foreground">
          Lancar um emprestimo exige {permissoesFaltantes(context.permissoes).join(", ")}.
        </p>
      </main>
    );
  }

  // Reutiliza a listagem de Devedores em vez de criar uma busca paralela: duas
  // fontes para o mesmo dado divergem com o tempo.
  const listagem = await listDevedores(
    cookieStore,
    context,
    resolveDevedoresFilters({ size: "100" }),
    dependencies,
  );
  if (listagem.kind === "problem" && listagem.problem.status === 401) {
    redirect(destinoRecuperacao);
  }

  // listDevedores devolve listagem ou devedor unico conforme o filtro; aqui so
  // a listagem interessa.
  const devedores: readonly DevedorResumo[] =
    listagem.kind === "ready" && "items" in listagem.data
      ? listagem.data.items.map((devedor) => ({
          id: devedor.id,
          nome: devedor.nome,
          documento: devedor.documento,
        }))
      : [];

  return (
    <main className="grid gap-4 p-6" id="conteudo-principal">
      <div>
        <p className="text-sm text-muted-foreground">Operacao</p>
        <h1 className="text-2xl font-semibold">Novo emprestimo</h1>
      </div>
      <LancamentoWizard
        action={lancarEmprestimoAction}
        devedores={devedores}
        initialState={INITIAL_LANCAMENTO_ACTION_STATE}
      />
    </main>
  );
}
