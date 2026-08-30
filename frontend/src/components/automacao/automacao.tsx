import { redirect } from "next/navigation";
import type { ReactNode } from "react";

import {
  hasExactAutomacaoPermission,
  JOB_CANCEL_PERMISSION,
  JOB_READ_PERMISSION,
  JOB_RETRY_PERMISSION,
  NOTIFICATION_READ_PERMISSION,
  NOTIFICATION_RECONCILE_PERMISSION,
  TEMPLATE_MANAGE_PERMISSION,
  type AutomacaoFilters,
  type AutomacaoProblem,
  type AutomacaoReadResult,
  type Job,
  type JobList,
  type Notification,
  type NotificationList,
  type TemplateList,
} from "../../lib/automacao/automacao-policy";
import { Alert, AlertDescription, AlertTitle } from "../ui/alert";
import { Button } from "../ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/card";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import { Skeleton } from "../ui/skeleton";

import { AutomacaoActions, type AutomacaoActionsProps } from "./automacao-actions.client";

export type AutomacaoAdminProps = Readonly<{
  actions: AutomacaoActionsProps;
  filters: AutomacaoFilters;
  job: Promise<AutomacaoReadResult<Job | null>>;
  jobs: Promise<AutomacaoReadResult<JobList>>;
  notification: Promise<AutomacaoReadResult<Notification | null>>;
  notifications: Promise<AutomacaoReadResult<NotificationList>>;
  permissions: readonly string[];
  recoveryHref: string;
  templates: Promise<AutomacaoReadResult<TemplateList>>;
}>;

function formatDate(value: string | null): string {
  if (!value) return "Sem data";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short", timeZone: "America/Sao_Paulo" }).format(parsed);
}

export function AutomacaoLoadingState() {
  return (
    <Card className="min-w-0">
      <CardHeader>
        <CardTitle>Automacao</CardTitle>
        <CardDescription>loading jobs, templates e notificacoes...</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-3" role="status" aria-label="loading Automacao">
        <Skeleton className="h-8 w-1/3" />
        <Skeleton className="h-48 w-full" />
      </CardContent>
    </Card>
  );
}

export function AutomacaoProblemState({ problem }: Readonly<{ problem: AutomacaoProblem }>) {
  const neutral404 = problem.status === 404;
  return (
    <Alert role="alert" variant="danger">
      <AlertTitle>{neutral404 ? "Automacao nao encontrada ou indisponivel (404)" : `Erro ${problem.status}`}</AlertTitle>
      <AlertDescription>
        {neutral404 ? "Automacao nao encontrada ou indisponivel." : problem.mensagem} Correlation ID: {problem.correlationId}
      </AlertDescription>
    </Alert>
  );
}

function DeniedState({ children = "denied: voce nao possui permissao exata para Automacao." }: Readonly<{ children?: ReactNode }>) {
  return <Alert><AlertTitle>denied</AlertTitle><AlertDescription>{children}</AlertDescription></Alert>;
}

function SectionResult<T>({ result, recoveryHref, children }: Readonly<{
  children(data: T): ReactNode;
  recoveryHref: string;
  result: AutomacaoReadResult<T>;
}>) {
  if (result.kind === "denied") return <DeniedState />;
  if (result.kind === "problem") {
    if (result.problem.status === 401) redirect(recoveryHref);
    return <AutomacaoProblemState problem={result.problem} />;
  }
  return children(result.data);
}

function FilterForm({ filters }: Readonly<{ filters: AutomacaoFilters }>) {
  return (
    <form className="grid gap-3 rounded-lg border bg-card p-4 md:grid-cols-[repeat(3,minmax(0,1fr))_auto]" method="get">
      <div className="grid gap-2">
        <Label htmlFor="automacao-filter-job">Job</Label>
        <Input defaultValue={filters.jobId ?? ""} id="automacao-filter-job" name="job_id" placeholder="ID do job, se houver" />
      </div>
      <div className="grid gap-2">
        <Label htmlFor="automacao-filter-notification">Notificacao</Label>
        <Input defaultValue={filters.notificationId ?? ""} id="automacao-filter-notification" name="notification_id" placeholder="ID da notificacao, se houver" />
      </div>
      <div className="grid gap-2">
        <Label htmlFor="automacao-filter-size">Itens por pagina</Label>
        <Input defaultValue={filters.size} id="automacao-filter-size" max={100} min={1} name="size" type="number" />
      </div>
      <Button className="self-end" type="submit">Consultar Automacao</Button>
    </form>
  );
}

function JobsView({ jobs }: Readonly<{ jobs: JobList }>) {
  if (jobs.items.length === 0) return <p role="status">empty: nenhum job retornado para a Carteira do contexto.</p>;
  return (
    <div aria-label="Jobs de Automacao com overflow" className="overflow-x-auto rounded-md border" data-state="overflow" role="region" tabIndex={0}>
      <table className="w-full min-w-[68rem] text-left text-sm">
        <caption className="sr-only">Jobs de Automacao retornados pelo backend</caption>
        <thead className="bg-muted">
          <tr><th className="p-2">Tipo</th><th className="p-2">Estado</th><th className="p-2">Tentativas</th><th className="p-2">Executar em</th><th className="p-2">Correlation</th><th className="p-2">Detalhe</th></tr>
        </thead>
        <tbody>
          {jobs.items.map((job) => (
            <tr className="border-t" key={job.id}>
              <td className="break-words p-2 font-semibold">{job.tipo}<span className="block text-xs text-muted-foreground">{job.origem_tipo}</span></td>
              <td className="p-2">{job.estado}</td>
              <td className="p-2">{job.tentativas}/{job.max_tentativas}</td>
              <td className="p-2"><time dateTime={job.executar_em}>{formatDate(job.executar_em)}</time></td>
              <td className="break-all p-2">{job.correlation_id}</td>
              <td className="p-2"><a className="font-semibold text-primary underline-offset-4 hover:underline" href={`/app/automacao?job_id=${job.id}`}>Consultar</a></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function NotificationsView({ notifications }: Readonly<{ notifications: NotificationList }>) {
  if (notifications.items.length === 0) return <p role="status">empty: nenhuma notificacao retornada para a Carteira do contexto.</p>;
  return (
    <div className="grid gap-3">
      {notifications.items.slice(0, 6).map((notification) => (
        <Card key={notification.id}>
          <CardHeader>
            <CardTitle>{notification.estado}</CardTitle>
            <CardDescription>Notificacao {notification.id}</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-2 text-sm">
            <p className="break-all">
              Job: {notification.job_id}
              {notification.lembrete_id
                ? `; lembrete: ${notification.lembrete_id}`
                : "; sem lembrete associado"}
            </p>
            <p>Provider message: {notification.provider_message_id ?? "Nao informado"}</p>
            <p>Codigo resultado: {notification.codigo_resultado ?? "Sem resultado"}</p>
            <p>Resultado em: {formatDate(notification.resultado_em)}</p>
            <a className="font-semibold text-primary underline-offset-4 hover:underline" href={`/app/automacao?notification_id=${notification.id}`}>Consultar notificacao</a>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function TemplatesView({ templates }: Readonly<{ templates: TemplateList }>) {
  if (templates.items.length === 0) return <p role="status">empty: nenhum template retornado.</p>;
  return (
    <div className="grid gap-3 md:grid-cols-2">
      {templates.items.slice(0, 6).map((template) => (
        <Card key={template.id}>
          <CardHeader>
            <CardTitle>{template.codigo} v{template.versao}</CardTitle>
            <CardDescription>Estado {template.estado}</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-2 text-sm">
            <p className="break-all">Template: {template.id}</p>
            <p className="break-all">Hash: {template.hash_conteudo}</p>
            <p>Aprovado em: {formatDate(template.aprovado_em)}</p>
            <p>Ativado em: {formatDate(template.ativado_em)}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function JobDetail({ job }: Readonly<{ job: Job | null }>) {
  if (!job) return <p role="status">Informe o ID do job para consultar um job especifico.</p>;
  return (
    <Card>
      <CardHeader><CardTitle>Job {job.estado}</CardTitle><CardDescription>Detalhe operacional read-only.</CardDescription></CardHeader>
      <CardContent className="grid gap-2 text-sm">
        <p className="break-all">ID: {job.id}</p>
        <p>Cancelamento solicitado: {job.cancelamento_solicitado ? "sim" : "nao"}</p>
        <p>Proxima execucao: {formatDate(job.proxima_execucao_em)}</p>
      </CardContent>
    </Card>
  );
}

function NotificationDetail({ notification }: Readonly<{ notification: Notification | null }>) {
  if (!notification) return <p role="status">Informe o ID da notificacao para consultar uma notificacao especifica.</p>;
  return (
    <Card>
      <CardHeader><CardTitle>Notificacao {notification.estado}</CardTitle><CardDescription>Detalhe para conciliacao governada.</CardDescription></CardHeader>
      <CardContent className="grid gap-2 text-sm">
        <p className="break-all">ID: {notification.id}</p>
        <p className="break-all">Provider: {notification.provider_message_id ?? "nao informado"}</p>
        <p className="break-all">Resultado: {notification.codigo_resultado ?? "sem codigo"}</p>
      </CardContent>
    </Card>
  );
}

export async function AutomacaoAdmin({ actions, filters, job, jobs, notification, notifications, permissions, recoveryHref, templates }: AutomacaoAdminProps) {
  const [jobResult, jobsResult, notificationResult, notificationsResult, templatesResult] = await Promise.all([job, jobs, notification, notifications, templates]);
  const canReadJobs = hasExactAutomacaoPermission(permissions, JOB_READ_PERMISSION);
  const canReadNotifications = hasExactAutomacaoPermission(permissions, NOTIFICATION_READ_PERMISSION);
  const canManageTemplates = hasExactAutomacaoPermission(permissions, TEMPLATE_MANAGE_PERMISSION);
  const canOperate = ([JOB_CANCEL_PERMISSION, JOB_RETRY_PERMISSION, TEMPLATE_MANAGE_PERMISSION, NOTIFICATION_RECONCILE_PERMISSION] as const).some((permission) => hasExactAutomacaoPermission(permissions, permission));
  return (
    <div className="grid min-w-0 gap-6">
      <header>
        <p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">Automacao operacional</p>
        <h1 className="text-balance text-3xl font-bold tracking-tight">Jobs, Templates e Notificacoes</h1>
        <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
          Acompanhe jobs, notificacoes e templates em um unico lugar, com conciliacao segura quando o envio precisa de conferencia.
        </p>
      </header>
      <FilterForm filters={filters} />
      {!canReadJobs ? <DeniedState>Sem permissao automacao.job.consultar para consultar jobs.</DeniedState> : null}
      {!canReadNotifications ? <DeniedState>Sem permissao notificacao.consultar para consultar notificacoes.</DeniedState> : null}
      {!canManageTemplates ? <DeniedState>Sem permissao notificacao.template.gerir para governar templates.</DeniedState> : null}
      <div className="grid min-w-0 gap-5 xl:grid-cols-2">
        <Card className="min-w-0">
          <CardHeader><CardTitle>Jobs</CardTitle><CardDescription>Total, estado e correlation retornados pelo backend.</CardDescription></CardHeader>
          <CardContent><SectionResult result={jobsResult} recoveryHref={recoveryHref}>{(data) => <JobsView jobs={data} />}</SectionResult></CardContent>
        </Card>
        <Card className="min-w-0">
          <CardHeader><CardTitle>Notificacoes</CardTitle><CardDescription>Resultados e reconciliacao de notificacao.</CardDescription></CardHeader>
          <CardContent><SectionResult result={notificationsResult} recoveryHref={recoveryHref}>{(data) => <NotificationsView notifications={data} />}</SectionResult></CardContent>
        </Card>
        <Card className="min-w-0">
          <CardHeader><CardTitle>Templates</CardTitle><CardDescription>Gestao por estados rascunho, aprovado, ativo e inativo.</CardDescription></CardHeader>
          <CardContent><SectionResult result={templatesResult} recoveryHref={recoveryHref}>{(data) => <TemplatesView templates={data} />}</SectionResult></CardContent>
        </Card>
        <SectionResult result={jobResult} recoveryHref={recoveryHref}>{(data) => <JobDetail job={data} />}</SectionResult>
        <SectionResult result={notificationResult} recoveryHref={recoveryHref}>{(data) => <NotificationDetail notification={data} />}</SectionResult>
      </div>
      {canOperate ? <AutomacaoActions {...actions} /> : <DeniedState>Sem permissao para comandos de Automacao.</DeniedState>}
      <p className="text-xs text-muted-foreground">Estados cobertos: loading, empty, denied, 400, 403, 404, 409, 422, 500 e overflow.</p>
    </div>
  );
}
