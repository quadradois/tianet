import { Suspense, type ReactNode } from "react";
import { redirect } from "next/navigation";

import { Alert, AlertDescription, AlertTitle } from "../ui/alert";
import { Button } from "../ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/card";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import { Skeleton } from "../ui/skeleton";
import type { ReportsSectionResult } from "../../lib/bff/relatorios.server";
import {
  MAX_REPORT_DATE,
  MIN_REPORT_DATE,
  type CashFlowReport,
  type DueDatesReport,
  type PaymentsReport,
  type ReportsPeriod,
  type ReportsPeriodResolution,
  type SummaryReport,
} from "../../lib/relatorios/relatorios-policy";

type ReportsProps = Readonly<{
  periodState: ReportsPeriodResolution;
  recoveryHref: string;
  summary?: Promise<ReportsSectionResult<SummaryReport>>;
  dueDates?: Promise<ReportsSectionResult<DueDatesReport>>;
  payments?: Promise<ReportsSectionResult<PaymentsReport>>;
  cashFlow?: Promise<ReportsSectionResult<CashFlowReport>>;
}>;

function formatDate(value: string): string {
  const [year, month, day] = value.split("-");
  return year && month && day ? `${day}/${month}/${year}` : value;
}

function officialIds(value: readonly string[]): string {
  return value.join(", ") || "sem IDs retornados";
}

function SectionCard({ title, description, children }: Readonly<{ title: string; description: string; children: ReactNode }>) {
  return (
    <Card className="min-w-0">
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}

export function ReportsLoadingState({ title }: Readonly<{ title: string }>) {
  return (
    <SectionCard title={title} description="Carregando relatorio oficial do backend...">
      <div aria-label={`Carregando ${title}`} className="grid gap-3" data-state="loading" role="status">
        <Skeleton className="h-8 w-2/3" />
        <Skeleton className="h-24 w-full" />
      </div>
    </SectionCard>
  );
}

function DeniedState() {
  return (
    <Alert data-state="denied">
      <AlertTitle>Sem permissao (403)</AlertTitle>
      <AlertDescription>Esta secao de Relatorios nao esta disponivel para o seu acesso.</AlertDescription>
    </Alert>
  );
}

function ProblemState({ result }: Readonly<{ result: Extract<ReportsSectionResult<unknown>, { kind: "problem" }> }>) {
  const neutral = result.problem.status === 404;
  return (
    <Alert variant="danger" role="alert">
      <AlertTitle>{neutral ? "Dados indisponiveis" : "Nao foi possivel carregar"}</AlertTitle>
      <AlertDescription>
        {neutral ? "Dados de relatorio nao encontrados ou indisponiveis." : result.problem.mensagem}{" "}
        Correlation ID: {result.problem.correlationId}
      </AlertDescription>
    </Alert>
  );
}

function MissingPeriodState() {
  return (
    <Alert data-state="empty">
      <AlertTitle>Defina periodo</AlertTitle>
      <AlertDescription>Informe data de referencia, inicio e fim para consultar os relatorios oficiais. Nenhuma data automatica foi inventada.</AlertDescription>
    </Alert>
  );
}

function InvalidPeriodState() {
  return (
    <Alert variant="danger" role="alert">
      <AlertTitle>Periodo invalido (400)</AlertTitle>
      <AlertDescription>Use datas reais entre {MIN_REPORT_DATE} e {MAX_REPORT_DATE}, com inicio menor ou igual ao fim. Nenhuma consulta foi executada.</AlertDescription>
    </Alert>
  );
}

function SectionResult<T>({ result, recoveryHref, children }: Readonly<{
  result: ReportsSectionResult<T>;
  recoveryHref: string;
  children(data: T): ReactNode;
}>) {
  if (result.kind === "denied") return <DeniedState />;
  if (result.kind === "problem") {
    if (result.problem.status === 401) redirect(recoveryHref);
    return <ProblemState result={result} />;
  }
  return children(result.data);
}

function Metric({ label, value }: Readonly<{ label: string; value: string | number }>) {
  return (
    <div className="rounded-md border bg-muted/30 p-3">
      <dt className="text-xs font-semibold text-muted-foreground">{label}</dt>
      <dd className="mt-1 break-words text-lg font-semibold tabular-nums">{value}</dd>
    </div>
  );
}

export function SummaryReportView({ data }: Readonly<{ data: SummaryReport }>) {
  return (
    <dl className="grid gap-3 sm:grid-cols-2 2xl:grid-cols-4" aria-label="Resumo oficial">
      <Metric label="Operacoes" value={data.total_operacoes} />
      <Metric label="Ativas" value={data.operacoes_ativas} />
      <Metric label="Quitadas" value={data.operacoes_quitadas} />
      <Metric label="Acertos pendentes" value={data.acertos_pendentes} />
      <Metric label="Ainda na rua" value={data.principal_a_receber} />
      <Metric label="Total realizado" value={data.total_realizado} />
      <Metric label="Data de referencia" value={formatDate(data.data_referencia)} />
    </dl>
  );
}

export function DueDatesReportView({ data }: Readonly<{ data: DueDatesReport }>) {
  if (data.itens.length === 0) return <p role="status">empty: nenhum acerto retornado para a data selecionada.</p>;
  return (
    <div aria-label="Acertos oficiais" className="overflow-x-auto rounded-md border" role="region" tabIndex={0}>
      <table className="w-full min-w-[720px] text-left text-xs">
        <caption className="sr-only">Acertos oficiais retornados pelo backend</caption>
        <thead className="bg-muted">
          <tr><th className="p-2">Acerto em</th><th className="p-2">Situacao</th><th className="p-2">Dia combinado</th><th className="p-2">Dias sem pagamento</th><th className="p-2">Emprestado</th><th className="p-2">Devedor</th></tr>
        </thead>
        <tbody>
          {data.itens.map((item) => (
            <tr className="border-t" key={item.emprestimo_id}>
              <td className="p-2"><time dateTime={item.acerto_em}>{formatDate(item.acerto_em)}</time></td>
              <td className="break-words p-2">{item.situacao}</td>
              <td className="p-2 tabular-nums">{item.dia_de_acerto}</td>
              <td className="p-2 tabular-nums">{item.dias_sem_pagamento}</td>
              <td className="p-2 tabular-nums">{item.principal_original}</td>
              <td className="break-all p-2">{item.devedor_id}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function PaymentsReportView({ data }: Readonly<{ data: PaymentsReport }>) {
  if (data.pagamentos[0] === undefined && data.operacoes_quitadas[0] === undefined) return <p role="status">empty: nenhum pagamento ou encerramento retornado no periodo.</p>;
  return (
    <div className="grid gap-3">
      <p className="text-sm text-muted-foreground">Total realizado oficial: <span className="tabular-nums">{data.total_realizado}</span></p>
      <div aria-label="Pagamentos oficiais" className="overflow-x-auto rounded-md border" role="region" tabIndex={0}>
        <table className="w-full min-w-[660px] text-left text-xs">
          <caption className="sr-only">Pagamentos oficiais retornados pelo backend</caption>
          <thead className="bg-muted"><tr><th className="p-2">Recebido em</th><th className="p-2">Estado</th><th className="p-2">Valor</th><th className="p-2">Pagamento</th></tr></thead>
          <tbody>{data.pagamentos.map((item) => <tr className="border-t" key={item.pagamento_id}><td className="p-2"><time dateTime={item.recebido_em}>{formatDate(item.recebido_em)}</time></td><td className="p-2">{item.estado}</td><td className="p-2 tabular-nums">{item.valor_recebido}</td><td className="break-all p-2">{item.pagamento_id}</td></tr>)}</tbody>
        </table>
      </div>
      <p className="break-all text-xs text-muted-foreground">Operacoes quitadas retornadas: <span>{officialIds(data.operacoes_quitadas)}</span></p>
    </div>
  );
}

export function CashFlowReportView({ data }: Readonly<{ data: CashFlowReport }>) {
  if (data.itens.length === 0) return <p role="status">empty: nenhum acerto ou recebimento retornado para o periodo.</p>;
  return (
    <div aria-label="Acertos e recebimentos por dia" className="max-h-96 overflow-auto rounded-md border" role="region" tabIndex={0}>
      <table className="w-full min-w-[720px] text-left text-xs">
        <caption className="sr-only">Acertos e recebimentos diarios retornados pelo backend</caption>
        <thead className="bg-muted"><tr><th className="p-2">Data</th><th className="p-2">Acertos no dia</th><th className="p-2">Realizado</th><th className="p-2">Pagamentos retornados</th></tr></thead>
        <tbody>{data.itens.map((item) => <tr className="border-t" key={item.data}><td className="p-2"><time dateTime={item.data}>{formatDate(item.data)}</time></td><td className="p-2 tabular-nums">{item.acertos}</td><td className="p-2 tabular-nums">{item.realizado}</td><td className="break-all p-2">{officialIds(item.pagamento_ids)}</td></tr>)}</tbody>
      </table>
    </div>
  );
}

async function SummarySection({ result, recoveryHref }: Readonly<{ result: NonNullable<ReportsProps["summary"]>; recoveryHref: string }>) {
  return <SectionCard title="Resumo oficial" description="Contagens e totais oficiais da Carteira."><SectionResult result={await result} recoveryHref={recoveryHref}>{(data) => <SummaryReportView data={data} />}</SectionResult></SectionCard>;
}

async function DueDatesSection({ result, recoveryHref }: Readonly<{ result: NonNullable<ReportsProps["dueDates"]>; recoveryHref: string }>) {
  return <SectionCard title="Vencimentos oficiais" description="Parcelas e situacoes oficiais na data de referencia."><SectionResult result={await result} recoveryHref={recoveryHref}>{(data) => <DueDatesReportView data={data} />}</SectionResult></SectionCard>;
}

async function PaymentsSection({ result, recoveryHref }: Readonly<{ result: NonNullable<ReportsProps["payments"]>; recoveryHref: string }>) {
  return <SectionCard title="Pagamentos oficiais" description="Pagamentos e encerramentos oficiais no periodo."><SectionResult result={await result} recoveryHref={recoveryHref}>{(data) => <PaymentsReportView data={data} />}</SectionResult></SectionCard>;
}

async function CashFlowSection({ result, recoveryHref }: Readonly<{ result: NonNullable<ReportsProps["cashFlow"]>; recoveryHref: string }>) {
  return <SectionCard title="Fluxo previsto e realizado" description="Fluxo diario oficial retornado pelo backend."><SectionResult result={await result} recoveryHref={recoveryHref}>{(data) => <CashFlowReportView data={data} />}</SectionResult></SectionCard>;
}

function Filters({ period }: Readonly<{ period?: ReportsPeriod }>) {
  return (
    <form className="grid gap-3 rounded-lg border bg-card p-4 sm:grid-cols-4 sm:items-end" method="get">
      <div className="grid gap-1">
        <Label htmlFor="data_referencia">Data de referencia</Label>
        <Input autoComplete="off" defaultValue={period?.referenceDate} id="data_referencia" max={MAX_REPORT_DATE} min={MIN_REPORT_DATE} name="data_referencia" required type="date" />
      </div>
      <div className="grid gap-1">
        <Label htmlFor="inicio">Inicio</Label>
        <Input autoComplete="off" defaultValue={period?.startDate} id="inicio" max={MAX_REPORT_DATE} min={MIN_REPORT_DATE} name="inicio" required type="date" />
      </div>
      <div className="grid gap-1">
        <Label htmlFor="fim">Fim</Label>
        <Input autoComplete="off" defaultValue={period?.endDate} id="fim" max={MAX_REPORT_DATE} min={MIN_REPORT_DATE} name="fim" required type="date" />
      </div>
      <Button type="submit">Consultar relatorios</Button>
    </form>
  );
}

export function Relatorios({ periodState, recoveryHref, summary, dueDates, payments, cashFlow }: ReportsProps) {
  const ready = periodState.kind === "ready";
  return (
    <div className="grid min-w-0 gap-6">
      <header className="grid gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">Relatorios operacionais</p>
          <h1 className="text-balance text-3xl font-bold tracking-tight">Relatorios</h1>
          <p className="mt-2 max-w-3xl text-sm text-muted-foreground">Apresentacao somente leitura das respostas oficiais. Nenhum valor financeiro e somado ou recalculado no browser/BFF.</p>
          <p className="sr-only">Estados cobertos: 400 403 404 500.</p>
        </div>
        {ready ? <Filters period={periodState.period} /> : <Filters />}
        {periodState.kind === "missing" && <MissingPeriodState />}
        {periodState.kind === "invalid" && <InvalidPeriodState />}
      </header>
      {ready && summary && dueDates && payments && cashFlow && (
        <div className="grid min-w-0 gap-5 xl:grid-cols-2">
          <Suspense fallback={<ReportsLoadingState title="Resumo oficial" />}><SummarySection recoveryHref={recoveryHref} result={summary} /></Suspense>
          <Suspense fallback={<ReportsLoadingState title="Vencimentos oficiais" />}><DueDatesSection recoveryHref={recoveryHref} result={dueDates} /></Suspense>
          <Suspense fallback={<ReportsLoadingState title="Pagamentos oficiais" />}><PaymentsSection recoveryHref={recoveryHref} result={payments} /></Suspense>
          <Suspense fallback={<ReportsLoadingState title="Fluxo previsto e realizado" />}><CashFlowSection recoveryHref={recoveryHref} result={cashFlow} /></Suspense>
        </div>
      )}
    </div>
  );
}
