import { Suspense, type ReactNode } from "react";
import { redirect } from "next/navigation";

import { Alert, AlertDescription, AlertTitle } from "../ui/alert";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/card";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import { Skeleton } from "../ui/skeleton";
import { CashFlowReportView } from "../relatorios/relatorios";
import type { components } from "../../lib/api/openapi.generated";
import type { DashboardSectionResult } from "../../lib/bff/dashboard.server";
import { MAX_REFERENCE_DATE, MIN_REFERENCE_DATE, type DashboardPeriod } from "../../lib/dashboard/dashboard-policy";
import { moeda } from "../../lib/formato/brasileiro";

type Summary = components["schemas"]["ResumoCarteiraResponse"];
type DueDates = components["schemas"]["VencimentosInadimplenciaResponse"];
type Agenda = components["schemas"]["AgendaOperacionalResponse"];
type CollectionQueue = components["schemas"]["FilaCobrancaResponse"];
type CashFlowReport = components["schemas"]["FluxoPrevistoRealizadoResponse"];

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
  fluxo: Promise<DashboardSectionResult<CashFlowReport>>;
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
    <SectionCard title={title} description="Carregando dados...">
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

function KpiIcon({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-muted text-primary" aria-hidden="true">
      {children}
    </span>
  );
}

function KpiCard({ label, value, icon, accent, badge, hint }: Readonly<{
  label: string;
  value: string | number;
  icon: ReactNode;
  accent?: "risco" | "projecao" | undefined;
  badge?: string;
  hint?: string;
}>) {
  const valueClass = accent === "risco" ? "text-destructive" : "text-foreground";
  return (
    <div className="flex flex-col gap-3 rounded-xl border bg-card p-4">
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</span>
        <KpiIcon>{icon}</KpiIcon>
      </div>
      <p className={`text-2xl font-semibold tabular-nums ${valueClass}`}>{value}</p>
      {badge ? (
        <span className="w-fit rounded-full bg-muted px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">{badge}</span>
      ) : null}
      {hint ? <p className="text-[11px] text-muted-foreground">{hint}</p> : null}
    </div>
  );
}

function WalletIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5">
      <path d="M3 7h15a2 2 0 0 1 2 2v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7Z" />
      <path d="M3 7V5a2 2 0 0 1 2-2h11" />
      <circle cx="16" cy="12" r="1" />
    </svg>
  );
}

function CoinsIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5">
      <ellipse cx="9" cy="7" rx="5" ry="2.5" />
      <path d="M4 7v5c0 1.4 2.2 2.5 5 2.5s5-1.1 5-2.5V7" />
      <ellipse cx="15" cy="14" rx="5" ry="2.5" />
      <path d="M10 14v5c0 1.4 2.2 2.5 5 2.5s5-1.1 5-2.5v-5" />
    </svg>
  );
}

function TrendingUpIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5">
      <path d="M3 17l6-6 4 4 8-8" />
      <path d="M17 7h4v4" />
    </svg>
  );
}

function LayersIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5">
      <path d="M12 3l9 5-9 5-9-5 9-5Z" />
      <path d="M3 12l9 5 9-5" />
      <path d="M3 17l9 5 9-5" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5">
      <circle cx="12" cy="12" r="9" />
      <path d="M8 12l3 3 5-6" />
    </svg>
  );
}

function AlertIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5">
      <path d="M12 3l9 16H3l9-16Z" />
      <path d="M12 10v4" />
      <path d="M12 17h.01" />
    </svg>
  );
}

export function SummaryHero({ data }: Readonly<{ data: Summary }>) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
      <KpiCard label="Caixa (recebido)" value={moeda(data.total_realizado)} icon={<WalletIcon />} />
      <KpiCard label="Emprestado (na rua)" value={moeda(data.principal_a_receber)} icon={<CoinsIcon />} />
      <KpiCard
        label="Projecao de juros (12m)"
        value={moeda(data.projecao_juros)}
        icon={<TrendingUpIcon />}
        accent="projecao"
        badge="projecao"
        hint="estimativa sobre o saldo atual"
      />
      <KpiCard label="Operacoes ativas" value={data.operacoes_ativas} icon={<LayersIcon />} />
      <KpiCard label="Quitadas" value={data.operacoes_quitadas} icon={<CheckIcon />} />
      <KpiCard
        label="Inadimplencia"
        value={data.acertos_pendentes}
        icon={<AlertIcon />}
        accent={data.acertos_pendentes > 0 ? "risco" : undefined}
      />
    </div>
  );
}

export function DueDatesView({ data }: Readonly<{ data: DueDates }>) {
  if (data.itens.length === 0) return <p role="status">Nenhum acerto retornado para a data selecionada.</p>;
  return (
    <>
      <ul className="grid gap-2 sm:hidden" aria-label="Acertos retornados">
        {data.itens.map((item) => <li className="rounded-md border p-3" key={item.emprestimo_id}><strong><time dateTime={item.acerto_em}>{formatDate(item.acerto_em)}</time></strong><dl className="mt-2 grid grid-cols-2 gap-2 text-sm"><div><dt className="text-muted-foreground">Situacao</dt><dd>{item.situacao}</dd></div><div><dt className="text-muted-foreground">Dia combinado</dt><dd className="tabular-nums">{item.dia_de_acerto}</dd></div><div><dt className="text-muted-foreground">Dias sem pagamento</dt><dd className="tabular-nums">{item.dias_sem_pagamento}</dd></div><div><dt className="text-muted-foreground">Emprestado</dt><dd className="tabular-nums">{moeda(item.principal_original)}</dd></div></dl></li>)}
      </ul>
      <div aria-label="Acertos retornados" className="hidden overflow-x-auto rounded-md border sm:block" role="region" tabIndex={0}>
        <table className="w-full table-fixed text-left text-xs">
          <caption className="sr-only">Acertos e situacoes retornados pelo sistema</caption>
          <thead className="bg-muted"><tr><th className="p-2">Acerto em</th><th className="p-2">Situacao</th><th className="p-2">Dia combinado</th><th className="p-2">Dias sem pagamento</th><th className="p-2">Emprestado</th></tr></thead>
          <tbody>{data.itens.map((item) => <tr className="border-t" key={item.emprestimo_id}><td className="break-words p-2"><time dateTime={item.acerto_em}>{formatDate(item.acerto_em)}</time></td><td className="break-words p-2">{item.situacao}</td><td className="break-words p-2 tabular-nums">{item.dia_de_acerto}</td><td className="break-words p-2 tabular-nums">{item.dias_sem_pagamento}</td><td className="break-words p-2 tabular-nums">{moeda(item.principal_original)}</td></tr>)}</tbody>
        </table>
      </div>
    </>
  );
}

export function AgendaView({ data }: Readonly<{ data: Agenda }>) {
  if (data.compromissos.length === 0 && data.lembretes.length === 0) return <p role="status">Nenhum compromisso ou lembrete retornado para a janela.</p>;
  return (
    <div className="grid gap-4">
      <p className="text-sm text-muted-foreground">Total: <span className="tabular-nums">{data.total}</span></p>
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
        <ul className="divide-y">{data.items.map((item) => <li className="min-w-0 p-3" key={item.caso_id}><strong className="break-words">{item.titulo}</strong><p className="text-sm text-muted-foreground">{item.estado} · Pendente: <span className="tabular-nums">{moeda(item.total_pendente)}</span></p><p className="break-all text-xs text-muted-foreground">Caso {item.caso_id}</p></li>)}</ul>
      </div>
    </div>
  );
}

async function SummarySection({ summary, fluxo, recoveryHref }: Readonly<{
  summary: DashboardProps["summary"];
  fluxo: DashboardProps["fluxo"];
  recoveryHref: string;
}>) {
  const [summaryResult, fluxoResult] = await Promise.all([summary, fluxo]);
  return (
    <SectionCard title="Cockpit da Carteira" description="Visao executiva da operacao na data escolhida.">
      <SectionResult result={summaryResult} recoveryHref={recoveryHref}>
        {(data) => (
          <div className="grid gap-5">
            <SummaryHero data={data} />
            <SectionResult result={fluxoResult} recoveryHref={recoveryHref}>
              {(fluxoData) => (
                <div className="grid gap-2">
                  <h3 className="text-sm font-semibold text-foreground">Previsao de fluxo de caixa (mes)</h3>
                  <CashFlowReportView data={fluxoData} />
                </div>
              )}
            </SectionResult>
          </div>
        )}
      </SectionResult>
    </SectionCard>
  );
}

async function DueDatesSection({ dueDates, recoveryHref }: Readonly<{ dueDates: DashboardProps["dueDates"]; recoveryHref: string }>) {
  return (
    <SectionCard title="Acertos do dia" description="Pagamentos e acertos com vencimento na data escolhida.">
      <SectionResult result={await dueDates} recoveryHref={recoveryHref}>
        {(data) => <DueDatesView data={data} />}
      </SectionResult>
    </SectionCard>
  );
}

async function AgendaSection({ agenda, recoveryHref }: Readonly<{ agenda: DashboardProps["agenda"]; recoveryHref: string }>) {
  return (
    <SectionCard title="Agenda do dia" description="Compromissos e lembretes previstos para o periodo.">
      <SectionResult result={await agenda} recoveryHref={recoveryHref}>
        {(data) => <AgendaView data={data} />}
      </SectionResult>
    </SectionCard>
  );
}

async function CollectionSection({ collection, recoveryHref }: Readonly<{ collection: DashboardProps["collection"]; recoveryHref: string }>) {
  return (
    <SectionCard title="Fila de cobranca" description="Preview somente leitura dos casos ativos da Carteira.">
      <SectionResult result={await collection} recoveryHref={recoveryHref}>
        {(data) => <CollectionView data={data} />}
      </SectionResult>
    </SectionCard>
  );
}

export function InvalidPeriodState() {
  return <Alert variant="danger" role="alert"><AlertTitle>Periodo invalido (400)</AlertTitle><AlertDescription>Informe uma data real no formato YYYY-MM-DD. Nenhuma consulta operacional foi executada.</AlertDescription></Alert>;
}

export function Dashboard({ period, recoveryHref, summary, dueDates, agenda, collection, fluxo }: DashboardProps) {
  return (
    <div className="grid min-w-0 gap-6">
      <header className="grid gap-4">
        <div className="grid gap-1">
          <h1 className="text-2xl font-semibold">Inicio</h1>
          <p className="text-sm text-muted-foreground">
            Visao executiva das operacoes na data de referencia.
          </p>
        </div>
        <form className="grid gap-3 sm:max-w-sm" method="get">
          <div className="grid gap-1.5">
            <Label htmlFor="reference-date">Data de referencia</Label>
            <Input
              defaultValue={period.referenceDate}
              id="reference-date"
              max={MAX_REFERENCE_DATE}
              min={MIN_REFERENCE_DATE}
              name="ref"
              type="date"
            />
          </div>
        </form>
      </header>
      <div className="grid min-w-0 gap-5 xl:grid-cols-2">
        <div className="min-w-0 xl:col-span-2">
          <Suspense fallback={<DashboardLoadingState title="Cockpit da Carteira" />}>
            <SummarySection summary={summary} fluxo={fluxo} recoveryHref={recoveryHref} />
          </Suspense>
        </div>
        <Suspense fallback={<DashboardLoadingState title="Acertos do dia" />}>
          <DueDatesSection dueDates={dueDates} recoveryHref={recoveryHref} />
        </Suspense>
        <Suspense fallback={<DashboardLoadingState title="Agenda do dia" />}>
          <AgendaSection agenda={agenda} recoveryHref={recoveryHref} />
        </Suspense>
        <Suspense fallback={<DashboardLoadingState title="Fila de cobranca" />}>
          <CollectionSection collection={collection} recoveryHref={recoveryHref} />
        </Suspense>
      </div>
    </div>
  );
}
