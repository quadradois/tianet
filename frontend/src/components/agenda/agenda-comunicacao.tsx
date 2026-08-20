import { redirect } from "next/navigation";
import type { ReactNode } from "react";

import {
  AGENDA_COMMITMENT_MANAGE_PERMISSION,
  AGENDA_REMINDER_MANAGE_PERMISSION,
  COMMUNICATION_REGISTER_PERMISSION,
  NOTIFICATION_RECONCILE_PERMISSION,
  hasExactPermission,
  type AgendaActionState,
  type AgendaFilters,
  type AgendaItem,
  type AgendaProblem,
  type AgendaReadResult,
  type AgendaResponse,
  type CommunicationFilters,
  type CommunicationHistory,
  type Reminder,
} from "../../lib/agenda/agenda-policy";
import { Alert, AlertDescription, AlertTitle } from "../ui/alert";
import { Button } from "../ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/card";
import { Label } from "../ui/label";
import { Skeleton } from "../ui/skeleton";

import {
  AgendaItemCommandForm,
  CommitmentForm,
  CommunicationForm,
  ReminderCommandForm,
  ReminderForm,
} from "./agenda-command-dialog.client";

type Action = (state: AgendaActionState, formData: FormData) => Promise<AgendaActionState>;

type AgendaComunicacaoPageProps = Readonly<{
  action: Action;
  actionState: AgendaActionState;
  agenda: AgendaReadResult<AgendaResponse>;
  agendaFilters: AgendaFilters;
  comunicacoes: AgendaReadResult<CommunicationHistory>;
  communicationFilters: CommunicationFilters;
  permissions: readonly string[];
  recoveryHref: string;
}>;

const DATE_TIME_FORMATTER = new Intl.DateTimeFormat("pt-BR", {
  dateStyle: "short",
  timeStyle: "short",
  timeZone: "America/Sao_Paulo",
});

function formatDateTime(value: string): string {
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : DATE_TIME_FORMATTER.format(parsed);
}

export function AgendaLoadingState() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Agenda e Comunicacao</CardTitle>
        <CardDescription>Carregando agenda e historico de comunicacao...</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-3" role="status" aria-label="loading Agenda">
        <Skeleton className="h-8 w-1/3" />
        <Skeleton className="h-48 w-full" />
      </CardContent>
    </Card>
  );
}

function ProblemState({ problem }: Readonly<{ problem: AgendaProblem }>) {
  const neutral404 = problem.status === 404;
  return (
    <Alert role="alert" variant="danger">
      <AlertTitle>{neutral404 ? "Agenda ou comunicacao nao encontrada ou indisponivel (404)" : `Erro ${problem.status}`}</AlertTitle>
      <AlertDescription>
        {neutral404 ? "Agenda ou comunicacao nao encontrada ou indisponivel." : problem.mensagem} Correlation ID: {problem.correlationId}
      </AlertDescription>
    </Alert>
  );
}

function DeniedState({ children = "Voce nao possui permissao para Agenda/Comunicacao." }: Readonly<{ children?: ReactNode }>) {
  return <Alert><AlertTitle>Sem permissao</AlertTitle><AlertDescription>{children}</AlertDescription></Alert>;
}

function SectionResult<T>({ result, recoveryHref, children }: Readonly<{
  children(data: T): ReactNode;
  recoveryHref: string;
  result: AgendaReadResult<T>;
}>) {
  if (result.kind === "denied") return <DeniedState />;
  if (result.kind === "problem") {
    if (result.problem.status === 401) redirect(recoveryHref);
    return <ProblemState problem={result.problem} />;
  }
  return children(result.data);
}

function FilterForm({ agendaFilters, communicationFilters }: Readonly<{ agendaFilters: AgendaFilters; communicationFilters: CommunicationFilters }>) {
  return (
    <form className="grid gap-3 rounded-lg border bg-card p-4 md:grid-cols-[repeat(3,minmax(0,1fr))_auto]" method="get">
      <div className="grid gap-2">
        <Label htmlFor="agenda-estado">Estado</Label>
        <select className="min-h-(--size-control) rounded-md border bg-background px-3 text-sm" defaultValue={agendaFilters.estado ?? ""} id="agenda-estado" name="estado">
          <option value="">Todos</option>
          <option value="aberto">aberto</option>
          <option value="reagendado">reagendado</option>
          <option value="concluido">concluido</option>
          <option value="cancelado">cancelado</option>
        </select>
      </div>
      <div className="grid gap-2">
        <Label htmlFor="agenda-devedor-filtro">Devedor</Label>
        <input className="min-h-(--size-control) rounded-md border bg-background px-3 text-sm" defaultValue={agendaFilters.devedorId ?? communicationFilters.devedorId ?? ""} id="agenda-devedor-filtro" name="devedor_id" placeholder="ID do devedor, se houver" />
      </div>
      <div className="grid gap-2">
        <Label htmlFor="agenda-inicio">Janela inicio</Label>
        <input className="min-h-(--size-control) rounded-md border bg-background px-3 text-sm" defaultValue={agendaFilters.janelaInicio ?? ""} id="agenda-inicio" name="janela_inicio" placeholder="2026-08-14T00:00:00-03:00" />
      </div>
      <div className="grid gap-2">
        <Label htmlFor="agenda-fim">Janela fim</Label>
        <input className="min-h-(--size-control) rounded-md border bg-background px-3 text-sm" defaultValue={agendaFilters.janelaFim ?? ""} id="agenda-fim" name="janela_fim" placeholder="2026-08-15T23:59:59-03:00" />
      </div>
      <Button className="self-end" type="submit">Filtrar Agenda</Button>
    </form>
  );
}

function CommitmentCard({ action, actionState, item, permissions }: Readonly<{
  action: Action;
  actionState: AgendaActionState;
  item: AgendaItem;
  permissions: readonly string[];
}>) {
  const canManage = hasExactPermission(permissions, AGENDA_COMMITMENT_MANAGE_PERMISSION);
  const canReminder = hasExactPermission(permissions, AGENDA_REMINDER_MANAGE_PERMISSION);
  const canReconcile = hasExactPermission(permissions, NOTIFICATION_RECONCILE_PERMISSION);
  return (
    <Card>
      <CardHeader>
        <CardTitle>{item.titulo}</CardTitle>
        <CardDescription>Estado {item.estado}; compromisso acompanhado pela agenda.</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-3">
        <dl className="grid gap-2 text-sm md:grid-cols-2">
          <div><dt className="text-muted-foreground">Compromisso</dt><dd className="break-all">{item.agenda_item_id}</dd></div>
          <div><dt className="text-muted-foreground">Devedor</dt><dd className="break-all">{item.devedor_id}</dd></div>
          <div><dt className="text-muted-foreground">Previsto para</dt><dd><time dateTime={item.previsto_para}>{formatDateTime(item.previsto_para)}</time></dd></div>
          <div><dt className="text-muted-foreground">Emprestimo</dt><dd className="break-all">{item.emprestimo_id ?? "Nao vinculado"}</dd></div>
          <div><dt className="text-muted-foreground">Atualizado em</dt><dd>{item.atualizado_em ? <time dateTime={item.atualizado_em}>{formatDateTime(item.atualizado_em)}</time> : "Sem atualizacao"}</dd></div>
        </dl>
        {canManage ? <AgendaItemCommandForm action={action} commitment={item} initialState={actionState} /> : <DeniedState>Sem permissao para manter compromisso.</DeniedState>}
        {canReminder ? <ReminderForm action={action} commitment={item} initialState={actionState} /> : <DeniedState>Sem permissao para criar lembrete.</DeniedState>}
        {!canReconcile ? <p className="text-xs text-muted-foreground">Seu perfil nao permite conciliar envios de notificacao.</p> : null}
      </CardContent>
    </Card>
  );
}

function AgendaView({ action, actionState, data, permissions }: Readonly<{
  action: Action;
  actionState: AgendaActionState;
  data: AgendaResponse;
  permissions: readonly string[];
}>) {
  if (data.compromissos.length === 0 && data.lembretes.length === 0) return <p role="status">Nenhum compromisso ou lembrete encontrado para esta carteira.</p>;
  return (
    <div className="grid gap-5">
      <p className="text-sm text-muted-foreground">
        Total: <span className="tabular-nums">{data.total}</span>. A consulta mostra compromissos do periodo e seus lembretes.
      </p>
      <div aria-label="Agenda operacional" className="overflow-x-auto rounded-md border" data-state="overflow" role="region" tabIndex={0}>
        <table className="w-full min-w-[72rem] text-left text-sm">
          <caption className="sr-only">Compromissos da agenda operacional</caption>
          <thead className="bg-muted">
            <tr><th className="p-2">Titulo</th><th className="p-2">Estado</th><th className="p-2">Previsto</th><th className="p-2">Compromisso</th><th className="p-2">Devedor</th><th className="p-2">Atualizado</th></tr>
          </thead>
          <tbody>
            {data.compromissos.map((item) => (
              <tr className="border-t" key={item.agenda_item_id}>
                <td className="max-w-xs break-words p-2 font-semibold">{item.titulo}</td>
                <td className="p-2">{item.estado}</td>
                <td className="p-2"><time dateTime={item.previsto_para}>{formatDateTime(item.previsto_para)}</time></td>
                <td className="break-all p-2">{item.agenda_item_id}</td>
                <td className="break-all p-2">{item.devedor_id}</td>
                <td className="p-2">{item.atualizado_em ? formatDateTime(item.atualizado_em) : "Sem atualizacao"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {data.compromissos.slice(0, 2).map((item) => <CommitmentCard action={action} actionState={actionState} item={item} key={item.agenda_item_id} permissions={permissions} />)}
      <section className="grid gap-3">
        <h2 className="text-xl font-semibold">Lembretes</h2>
        {data.lembretes.length === 0 ? <p role="status">Nenhum lembrete encontrado.</p> : data.lembretes.slice(0, 3).map((reminder: Reminder) => (
          <Card key={reminder.lembrete_id}>
            <CardHeader>
              <CardTitle>{reminder.estado}</CardTitle>
              <CardDescription><time dateTime={reminder.horario}>{formatDateTime(reminder.horario)}</time></CardDescription>
            </CardHeader>
            <CardContent className="grid gap-3">
              <p className="break-words text-sm">{reminder.mensagem}</p>
              <p className="break-all text-xs text-muted-foreground">Lembrete {reminder.lembrete_id}; compromisso {reminder.agenda_item_id}</p>
              {hasExactPermission(permissions, AGENDA_REMINDER_MANAGE_PERMISSION) || hasExactPermission(permissions, NOTIFICATION_RECONCILE_PERMISSION)
                ? <ReminderCommandForm action={action} initialState={actionState} reminder={reminder} />
                : <DeniedState>Sem permissao para manter ou conciliar lembrete.</DeniedState>}
            </CardContent>
          </Card>
        ))}
      </section>
    </div>
  );
}

function CommunicationView({ data }: Readonly<{ data: CommunicationHistory }>) {
  if (data.registros.length === 0) return <p role="status">Nenhum registro de comunicacao encontrado para esta carteira.</p>;
  return (
    <div className="grid gap-3">
      <p className="text-sm text-muted-foreground">Historico de comunicacao: <span className="tabular-nums">{data.total}</span> registro(s).</p>
      {data.registros.slice(0, 5).map((record) => (
        <Card key={record.registro_id}>
          <CardHeader>
            <CardTitle>{record.canal}</CardTitle>
            <CardDescription><time dateTime={record.ocorrido_em}>{formatDateTime(record.ocorrido_em)}</time></CardDescription>
          </CardHeader>
          <CardContent className="grid gap-2 text-sm">
            <p className="break-words font-medium">{record.resumo}</p>
            <p className="break-words">{record.resultado}</p>
            <p className="break-all text-xs text-muted-foreground">Registro {record.registro_id}; devedor {record.devedor_id ?? "nao vinculado"}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

export function AgendaComunicacaoPage({ action, actionState, agenda, agendaFilters, comunicacoes, communicationFilters, permissions, recoveryHref }: AgendaComunicacaoPageProps) {
  const canCreateCommitment = hasExactPermission(permissions, AGENDA_COMMITMENT_MANAGE_PERMISSION);
  const canRegisterCommunication = hasExactPermission(permissions, COMMUNICATION_REGISTER_PERMISSION);
  return (
    <div className="grid min-w-0 gap-6">
      <header>
        <p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">Agenda e Comunicacao</p>
        <h1 className="text-balance text-3xl font-bold tracking-tight">Agenda e Comunicacao</h1>
        <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
          Organize retornos, lembretes e contatos feitos com os devedores.
        </p>
      </header>
      <FilterForm agendaFilters={agendaFilters} communicationFilters={communicationFilters} />
      <div className="grid gap-4 lg:grid-cols-2">
        {canCreateCommitment ? <CommitmentForm action={action} initialState={actionState} /> : <DeniedState>Sem permissao para criar compromisso.</DeniedState>}
        {canRegisterCommunication ? <CommunicationForm action={action} initialState={actionState} /> : <DeniedState>Sem permissao para registrar comunicacao.</DeniedState>}
      </div>
      <section className="grid gap-3">
        <h2 className="text-xl font-semibold">Compromissos e lembretes</h2>
        <SectionResult result={agenda} recoveryHref={recoveryHref}>
          {(data) => <AgendaView action={action} actionState={actionState} data={data} permissions={permissions} />}
        </SectionResult>
      </section>
      <section className="grid gap-3">
        <h2 className="text-xl font-semibold">Historico de comunicacao</h2>
        <SectionResult result={comunicacoes} recoveryHref={recoveryHref}>
          {(data) => <CommunicationView data={data} />}
        </SectionResult>
      </section>
      <p className="sr-only">Estados de carregamento, vazio, acesso negado, erro e listas com overflow sao tratados nesta tela.</p>
    </div>
  );
}
