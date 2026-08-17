import { Suspense, type ReactNode } from "react";
import { redirect } from "next/navigation";

import { Alert, AlertDescription, AlertTitle } from "../ui/alert";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/card";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import { Skeleton } from "../ui/skeleton";
import type { components } from "../../lib/api/openapi.generated";
import type { DashboardSectionResult } from "../../lib/bff/dashboard.server";
import { MAX_REFERENCE_DATE, MIN_REFERENCE_DATE, type DashboardPeriod } from "../../lib/dashboard/dashboard-policy";

type Summary = components["schemas"]["ResumoCarteiraResponse"];
type DueDates = components["schemas"]["VencimentosInadimplenciaResponse"];
type Agenda = components["schemas"]["AgendaOperacionalResponse"];
type CollectionQueue = components["schemas"]["FilaCobrancaResponse"];

const DATE_FORMATTER = new Intl.DateTimeFormat("pt-BR", {
  day: "2-digit",
  month: "2-digit",
  timeZone: "UTC",
  year: "numeric",
});
const DATE_TIME_FORMATTER = new Intl.DateTimeFormat("pt-BR", {
  dateStyle: "short",
  timeStyle: "short",
  timeZone: "America/Sao_Paulo",
});

function formatDate(value: string): string {
  const parsed = new Date(`${value}T00:00:00.000Z`);
  return Number.isNaN(parsed.getTime()) ? value : DATE_FORMATTER.format(parsed);
}

function formatDateTime(value: string): string {
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : DATE_TIME_FORMATTER.format(parsed);
}

type DashboardProps = Readonly<{
  period: DashboardPeriod;
  recoveryHref: string;
  summary: Promise<DashboardSectionResult<Summary>>;
  dueDates: Promise<DashboardSectionResult<DueDates>>;
  agenda: Promise<DashboardSectionResult<Agenda>>;
  collection: Promise<DashboardSectionResult<CollectionQueue>>;
}>;

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

export function DashboardLoadingState({ title }: Readonly<{ title: string }>) {
  return (
    <SectionCard title={title} description="Carregando dados oficiais do backend…">
      <div aria-label={`Carregando ${title}`} className="grid gap-3" role="status">
        <Skeleton className="h-8 w-2/3" />
        <Skeleton className="h-20 w-full" />
      </div>
    </SectionCard>
  );
}

function DeniedState() {
  return <Alert><AlertTitle>Sem permissao</AlertTitle><AlertDescription>Esta secao nao esta disponivel para o seu acesso.</AlertDescription></Alert>;
}

function ProblemState({ result }: Readonly<{ result: Extract<DashboardSectionResult<unknown>, { kind: "problem" }> }>) {
  const neutral = result.problem.status === 404;
  return (
    <Alert variant="danger" role="alert">
      <AlertTitle>{neutral ? "Dados indisponiveis" : "Nao foi possivel carregar"}</AlertTitle>
      <AlertDescription>
        {neutral ? "Dados nao encontrados ou indisponiveis." : result.problem.mensagem}{" "}
        Correlation ID: {result.problem.correlationId}
      </AlertDescription>
    </Alert>
  );
}

function SectionResult<T>({ result, recoveryHref, children }: Readonly<{
  result: DashboardSectionResult<T>;
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
  return <div className="rounded-md border bg-muted/30 p-3"><dt className="text-xs font-semibold text-muted-foreground">{label}</dt><dd className="mt-1 break-words text-lg font-semibold tabular-nums">{value}</dd></div>;
}

export function SummaryView({ data }: Readonly<{ data: Summary }>) {
  return (
    <dl className="grid gap-3 sm:grid-cols-2 2xl:grid-cols-4">
      <Metric label="Operacoes" value={data.total_operacoes} />
      <Metric label="Ativas" value={data.operacoes_ativas} />
      <Metric label="Quitadas" value={data.operacoes_quitadas} />
      <Metric label="Parcelas previstas" value={data.parcelas_previstas} />
      <Metric label="Parcelas vencidas" value={data.parcelas_vencidas} />
      <Metric label="Total previsto (oficial)" value={data.total_previsto} />
      <Metric label="Total realizado (oficial)" value={data.total_realizado} />
      <Metric label="Data de referencia" value={formatDate(data.data_referencia)} />
    </dl>
  );
}

export function DueDatesView({ data }: Readonly<{ data: DueDates }>) {
  if (data.itens.length === 0) return <p role="status">Nenhum vencimento retornado para a data selecionada.</p>;
  return (
    <>
      <ul className="grid gap-2 sm:hidden" aria-label="Vencimentos retornados">{data.itens.map((item) => <li className="rounded-md border p-3" key={item.parcela_id}><strong>Parcela {item.numero}</strong><dl className="mt-2 grid grid-cols-2 gap-2 text-sm"><div><dt className="text-muted-foreground">Vencimento</dt><dd><time dateTime={item.vencimento}>{formatDate(item.vencimento)}</time></dd></div><div><dt className="text-muted-foreground">Situacao</dt><dd>{item.situacao}</dd></div><div><dt className="text-muted-foreground">Previsto</dt><dd className="tabular-nums">{item.valor_previsto}</dd></div><div><dt className="text-muted-foreground">Liquidado</dt><dd className="tabular-nums">{item.valor_liquidado}</dd></div></dl></li>)}</ul>
      <div aria-label="Vencimentos retornados" className="hidden overflow-x-auto rounded-md border sm:block" role="region" tabIndex={0}>
        <table className="w-full table-fixed text-left text-xs">
          <caption className="sr-only">Parcelas e situacoes oficiais retornadas pelo backend</caption>
          <thead className="bg-muted"><tr><th className="p-2">Parcela</th><th className="p-2">Vencimento</th><th className="p-2">Situacao</th><th className="p-2">Previsto</th><th className="p-2">Liquidado</th></tr></thead>
          <tbody>{data.itens.map((item) => <tr className="border-t" key={item.parcela_id}><td className="break-words p-2 tabular-nums">{item.numero}</td><td className="break-words p-2"><time dateTime={item.vencimento}>{formatDate(item.vencimento)}</time></td><td className="break-words p-2">{item.situacao}</td><td className="break-words p-2 tabular-nums">{item.valor_previsto}</td><td className="break-words p-2 tabular-nums">{item.valor_liquidado}</td></tr>)}</tbody>
        </table>
      </div>
    </>
  );
}

export function AgendaView({ data }: Readonly<{ data: Agenda }>) {
  if (data.compromissos.length === 0 && data.lembretes.length === 0) return <p role="status">Nenhum compromisso ou lembrete retornado para a janela.</p>;
  return (
    <div className="grid gap-4">
      <p className="text-sm text-muted-foreground">Total oficial: <span className="tabular-nums">{data.total}</span></p>
      <ul className="grid gap-2" aria-label="Compromissos">
        {data.compromissos.map((item) => <li className="min-w-0 rounded-md border p-3" key={item.agenda_item_id}><strong className="break-words">{item.titulo}</strong><p className="text-sm text-muted-foreground"><time dateTime={item.previsto_para}>{formatDateTime(item.previsto_para)}</time> · {item.estado}</p></li>)}
      </ul>
      {data.lembretes.length > 0 && <ul className="grid gap-2" aria-label="Lembretes">{data.lembretes.map((item) => <li className="min-w-0 rounded-md border p-3" key={item.lembrete_id}><span className="break-words">{item.mensagem}</span><p className="text-sm text-muted-foreground"><time dateTime={item.horario}>{formatDateTime(item.horario)}</time> · {item.estado}</p></li>)}</ul>}
    </div>
  );
}

export function CollectionView({ data }: Readonly<{ data: CollectionQueue }>) {
  if (data.items.length === 0) return <p role="status">Nenhum caso ativo foi retornado para a Carteira.</p>;
  return (
    <div className="grid gap-3">
      <p className="text-sm text-muted-foreground">Total oficial: <span className="tabular-nums">{data.total}</span></p>
      <div aria-label="Fila de cobranca" className="max-h-80 overflow-auto rounded-md border" role="region" tabIndex={0}>
        <ul className="divide-y">{data.items.map((item) => <li className="min-w-0 p-3" key={item.caso_id}><strong className="break-words">{item.titulo}</strong><p className="text-sm text-muted-foreground">{item.estado} · Pendente: <span className="tabular-nums">{item.total_pendente}</span></p><p className="break-all text-xs text-muted-foreground">Caso {item.caso_id}</p></li>)}</ul>
      </div>
    </div>
  );
}

async function SummarySection({ result, recoveryHref }: Readonly<{ result: DashboardProps["summary"]; recoveryHref: string }>) {
  return <SectionCard title="Resumo da Carteira" description="Resumo da sua carteira."><SectionResult result={await result} recoveryHref={recoveryHref}>{(data) => <SummaryView data={data} />}</SectionResult></SectionCard>;
}

async function DueDatesSection({ result, recoveryHref }: Readonly<{ result: DashboardProps["dueDates"]; recoveryHref: string }>) {
  return <SectionCard title="Vencimentos" description="Parcelas e suas situacoes na data escolhida."><SectionResult result={await result} recoveryHref={recoveryHref}>{(data) => <DueDatesView data={data} />}</SectionResult></SectionCard>;
}

async function AgendaSection({ result, recoveryHref }: Readonly<{ result: DashboardProps["agenda"]; recoveryHref: string }>) {
  return <SectionCard title="Agenda do dia" description="Compromissos na janela inclusiva e os lembretes vinculados retornados pelo backend."><SectionResult result={await result} recoveryHref={recoveryHref}>{(data) => <AgendaView data={data} />}</SectionResult></SectionCard>;
}

async function CollectionSection({ result, recoveryHref }: Readonly<{ result: DashboardProps["collection"]; recoveryHref: string }>) {
  return <SectionCard title="Fila de cobranca" description="Preview somente leitura dos casos ativos da Carteira."><SectionResult result={await result} recoveryHref={recoveryHref}>{(data) => <CollectionView data={data} />}</SectionResult></SectionCard>;
}

export function InvalidPeriodState() {
  return <Alert variant="danger" role="alert"><AlertTitle>Periodo invalido (400)</AlertTitle><AlertDescription>Informe uma data real no formato YYYY-MM-DD. Nenhuma consulta operacional foi executada.</AlertDescription></Alert>;
}

export function Dashboard({ period, recoveryHref, summary, dueDates, agenda, collection }: DashboardProps) {
  return (
    <div className="grid min-w-0 gap-6">
      <header className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div><p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">Operacao diaria</p><h1 className="text-balance text-3xl font-bold tracking-tight">Dashboard</h1><p className="mt-2 max-w-3xl text-sm text-muted-foreground">Como esta a sua operacao hoje. Situacao da sua carteira na data escolhida.</p></div>
        <form className="flex flex-col gap-2 sm:flex-row sm:items-end" method="get">
          <div className="grid gap-1"><Label htmlFor="data_referencia">Data de referencia</Label><Input autoComplete="off" defaultValue={period.referenceDate} id="data_referencia" max={MAX_REFERENCE_DATE} min={MIN_REFERENCE_DATE} name="data_referencia" required type="date" /></div>
          <button className="min-h-(--size-control) rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground transition-colors hover:bg-primary/90" type="submit">Atualizar</button>
        </form>
      </header>
      <p className="text-xs text-muted-foreground"></p>
      <div className="grid min-w-0 gap-5 xl:grid-cols-2">
        <Suspense fallback={<DashboardLoadingState title="Resumo da Carteira" />}><SummarySection recoveryHref={recoveryHref} result={summary} /></Suspense>
        <Suspense fallback={<DashboardLoadingState title="Vencimentos" />}><DueDatesSection recoveryHref={recoveryHref} result={dueDates} /></Suspense>
        <Suspense fallback={<DashboardLoadingState title="Agenda do dia" />}><AgendaSection recoveryHref={recoveryHref} result={agenda} /></Suspense>
        <Suspense fallback={<DashboardLoadingState title="Fila de cobranca" />}><CollectionSection recoveryHref={recoveryHref} result={collection} /></Suspense>
      </div>
    </div>
  );
}
