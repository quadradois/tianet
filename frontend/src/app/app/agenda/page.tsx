import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { AgendaComunicacaoPage } from "@/components/agenda/agenda-comunicacao";
import { agendaCommandAction } from "@/app/app/agenda/actions";
import { ApiProblem, createRuntimeDependencies } from "@/lib/bff/backend.server";
import { recoveryAttemptCookieName } from "@/lib/bff/context.server";
import { currentOperationalContext } from "@/lib/bff/current-context.server";
import { listAgenda, listCommunications } from "@/lib/bff/agenda-comunicacao.server";
import { INITIAL_AGENDA_ACTION_STATE, resolveAgendaFilters, resolveCommunicationFilters } from "@/lib/agenda/agenda-policy";

export const metadata = {
  title: "Agenda e Comunicacao | TiaNet",
};

export default async function AgendaPage({ searchParams }: PageProps<"/app/agenda">) {
  const query = await searchParams;
  const agendaFilters = resolveAgendaFilters(query);
  const communicationFilters = resolveCommunicationFilters(query);
  const cookieStore = await cookies();
  const dependencies = createRuntimeDependencies();
  const recoveryHref = cookieStore.get(recoveryAttemptCookieName(dependencies.config)) ? "/login" : "/session/recover";
  const context = await currentOperationalContext();
  let agenda;
  let comunicacoes;
  try {
    [agenda, comunicacoes] = await Promise.all([
      listAgenda(cookieStore, context, agendaFilters, dependencies),
      listCommunications(cookieStore, context, communicationFilters, dependencies),
    ]);
  } catch (error) {
    if (error instanceof ApiProblem && error.status === 401) redirect(recoveryHref);
    throw error;
  }
  return (
    <AgendaComunicacaoPage
      action={agendaCommandAction}
      actionState={INITIAL_AGENDA_ACTION_STATE}
      agenda={agenda}
      agendaFilters={agendaFilters}
      comunicacoes={comunicacoes}
      communicationFilters={communicationFilters}
      permissions={context.permissoes}
      recoveryHref={recoveryHref}
    />
  );
}
