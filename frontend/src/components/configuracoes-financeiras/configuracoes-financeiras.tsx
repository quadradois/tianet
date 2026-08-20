import { Suspense, type ReactNode } from "react";
import { redirect } from "next/navigation";

import {
  CONFIGURACOES_ACTIVATE_PERMISSION,
  CONFIGURACOES_APPROVE_PERMISSION,
  CONFIGURACOES_MANAGE_PERMISSION,
  CALENDARIO_MANAGE_PERMISSION,
  MODALIDADE_MANAGE_PERMISSION,
  SNAPSHOT_CAPTURE_PERMISSION,
  formatOpaqueValue,
  hasExactPermission,
  type CalendarioFinanceiro,
  type ConfiguracaoFinanceira,
  type ConfiguracaoPermission,
  type ConfiguracaoState,
  type ConfiguracaoVigente,
  type ConfiguracoesFilters,
  type ModalidadeFinanceira,
} from "../../lib/configuracoes-financeiras/configuracoes-policy";

import { Alert, AlertDescription, AlertTitle } from "../ui/alert";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/card";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import { Skeleton } from "../ui/skeleton";
import { ConfiguracoesActions, type ConfiguracoesActionsProps } from "./configuracoes-actions.client";

type ConfiguracoesProps = Readonly<{
  filters: ConfiguracoesFilters;
  permissions: readonly string[];
  recoveryHref: string;
  actions: ConfiguracoesActionsProps;
  configuracoes: Promise<ConfiguracoesViewResult<readonly ConfiguracaoFinanceira[]>>;
  vigente: Promise<ConfiguracoesViewResult<ConfiguracaoVigente | null>>;
  modalidades: Promise<ConfiguracoesViewResult<readonly ModalidadeFinanceira[]>>;
  calendarios: Promise<ConfiguracoesViewResult<readonly CalendarioFinanceiro[]>>;
}>;

type ConfiguracoesViewProblem = Readonly<{
  codigo: string;
  correlationId: string;
  mensagem: string;
  status: number;
}>;

type ConfiguracoesViewResult<T> =
  | Readonly<{ kind: "ready"; data: T }>
  | Readonly<{ kind: "denied" }>
  | Readonly<{ kind: "problem"; problem: ConfiguracoesViewProblem }>;

function formatDate(value: string | null): string {
  if (!value) return "sem data";
  const [year, month, day] = value.split("-");
  return year && month && day ? `${day}/${month}/${year}` : value;
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

export function ConfiguracoesLoadingState({ title }: Readonly<{ title: string }>) {
  return (
    <SectionCard title={title} description="Carregando configuracao...">
      <div aria-label={`Carregando ${title}`} className="grid gap-3" data-state="loading" role="status">
        <Skeleton className="h-8 w-2/3" />
        <Skeleton className="h-24 w-full" />
      </div>
    </SectionCard>
  );
}

export function ProblemState({ result }: Readonly<{ result: Extract<ConfiguracoesViewResult<unknown>, { kind: "problem" }> }>) {
  const neutral = result.problem.status === 404;
  return (
    <Alert variant="danger" role="alert">
      <AlertTitle>{neutral ? "Configuracao indisponivel" : "Nao foi possivel carregar"}</AlertTitle>
      <AlertDescription>
        {neutral ? "Configuracao Financeira nao encontrada ou indisponivel." : result.problem.mensagem}{" "}
        Correlation ID: {result.problem.correlationId}
      </AlertDescription>
    </Alert>
  );
}

export function DeniedState() {
  return (
    <Alert data-state="denied">
      <AlertTitle>Sem permissao</AlertTitle>
      <AlertDescription>Configuracoes Financeiras nao estao disponiveis para o seu acesso.</AlertDescription>
    </Alert>
  );
}

function SectionResult<T>({ result, recoveryHref, children }: Readonly<{
  result: ConfiguracoesViewResult<T>;
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

function ConfigRow({ item }: Readonly<{ item: ConfiguracaoFinanceira }>) {
  return (
    <tr className="border-t">
      <td className="break-all p-2">{item.id}</td>
      <td className="p-2">{item.modalidade}</td>
      <td className="p-2">{item.estado}</td>
      <td className="p-2 tabular-nums">{item.versao}</td>
      <td className="p-2"><time dateTime={item.vigencia_inicio}>{formatDate(item.vigencia_inicio)}</time></td>
      <td className="p-2">{formatDate(item.vigencia_fim)}</td>
      <td className="p-2 tabular-nums">{item.total_eventos}</td>
      <td className="break-words p-2">{formatOpaqueValue(item.parametros)}</td>
    </tr>
  );
}

export function ConfiguracoesList({ data }: Readonly<{ data: readonly ConfiguracaoFinanceira[] }>) {
  if (data.length === 0) return <p role="status">Nenhuma configuracao financeira encontrada para os filtros.</p>;
  return (
    <div aria-label="Configuracoes oficiais" className="max-h-[28rem] overflow-auto rounded-md border" role="region" tabIndex={0}>
      <table className="w-full min-w-[920px] text-left text-xs">
        <caption className="sr-only">Configuracoes Financeiras retornadas pelo sistema</caption>
        <thead className="bg-muted">
          <tr><th className="p-2">ID</th><th className="p-2">Modalidade</th><th className="p-2">Estado</th><th className="p-2">Versao</th><th className="p-2">Inicio</th><th className="p-2">Fim</th><th className="p-2">Eventos</th><th className="p-2">Parametros oficiais</th></tr>
        </thead>
        <tbody>{data.map((item) => <ConfigRow item={item} key={item.id} />)}</tbody>
      </table>
    </div>
  );
}

export function VigenteView({ data }: Readonly<{ data: ConfiguracaoVigente | null }>) {
  if (data === null) return <p role="status">Defina modalidade e data de referencia para consultar a configuracao vigente.</p>;
  return (
    <dl className="grid gap-3 sm:grid-cols-2">
      <div className="rounded-md border bg-muted/30 p-3"><dt className="text-xs text-muted-foreground">Configuracao</dt><dd className="break-all font-semibold">{data.configuracao_id}</dd></div>
      <div className="rounded-md border bg-muted/30 p-3"><dt className="text-xs text-muted-foreground">Modalidade</dt><dd className="font-semibold">{data.modalidade}</dd></div>
      <div className="rounded-md border bg-muted/30 p-3"><dt className="text-xs text-muted-foreground">Versao</dt><dd className="font-semibold tabular-nums">{data.versao}</dd></div>
      <div className="rounded-md border bg-muted/30 p-3"><dt className="text-xs text-muted-foreground">Consultada em</dt><dd className="break-words font-semibold">{data.consultada_em}</dd></div>
      <div className="rounded-md border bg-muted/30 p-3 sm:col-span-2"><dt className="text-xs text-muted-foreground">Parametros oficiais</dt><dd className="break-words font-semibold">{formatOpaqueValue(data.parametros)}</dd></div>
    </dl>
  );
}

function SimpleList<T extends { id: string; codigo: string; nome: string }>({ items, label }: Readonly<{ items: readonly T[]; label: string }>) {
  if (items.length === 0) return <p role="status">Nenhum item encontrado.</p>;
  return (
    <ul aria-label={label} className="grid gap-2">
      {items.map((item) => <li className="break-words rounded-md border bg-muted/20 p-2" key={item.id}><strong>{item.codigo}</strong> — {item.nome}</li>)}
    </ul>
  );
}

async function ConfiguracoesSection({ result, recoveryHref }: Readonly<{ result: ConfiguracoesProps["configuracoes"]; recoveryHref: string }>) {
  return <SectionCard title="Configuracoes cadastradas" description="Lista da carteira operacional."><SectionResult result={await result} recoveryHref={recoveryHref}>{(data) => <ConfiguracoesList data={data} />}</SectionResult></SectionCard>;
}

async function VigenteSection({ result, recoveryHref }: Readonly<{ result: ConfiguracoesProps["vigente"]; recoveryHref: string }>) {
  return <SectionCard title="Configuracao vigente" description="Consulta por modalidade e data."><SectionResult result={await result} recoveryHref={recoveryHref}>{(data) => <VigenteView data={data} />}</SectionResult></SectionCard>;
}

async function ModalidadesSection({ result, recoveryHref }: Readonly<{ result: ConfiguracoesProps["modalidades"]; recoveryHref: string }>) {
  return <SectionCard title="Modalidades" description="Catalogo financeiro."><SectionResult result={await result} recoveryHref={recoveryHref}>{(data) => <SimpleList items={data} label="Modalidades financeiras" />}</SectionResult></SectionCard>;
}

async function CalendariosSection({ result, recoveryHref }: Readonly<{ result: ConfiguracoesProps["calendarios"]; recoveryHref: string }>) {
  return <SectionCard title="Calendarios" description="Calendarios financeiros."><SectionResult result={await result} recoveryHref={recoveryHref}>{(data) => <SimpleList items={data} label="Calendarios financeiros" />}</SectionResult></SectionCard>;
}

function Filters({ filters }: Readonly<{ filters: ConfiguracoesFilters }>) {
  const estadoOptions: readonly ConfiguracaoState[] = ["rascunho", "aprovada", "programada", "ativa", "substituida", "inativa"];
  return (
    <form className="grid gap-3 rounded-lg border bg-card p-4 md:grid-cols-4 md:items-end" method="get">
      <div className="grid gap-1">
        <Label htmlFor="modalidade">Modalidade</Label>
        <Input autoComplete="off" defaultValue={filters.modalidade} id="modalidade" name="modalidade" placeholder="consignado" />
      </div>
      <div className="grid gap-1">
        <Label htmlFor="data_referencia">Data de referencia</Label>
        <Input autoComplete="off" defaultValue={filters.dataReferencia} id="data_referencia" name="data_referencia" type="date" />
      </div>
      <div className="grid gap-1">
        <Label htmlFor="estado">Estado</Label>
        <select className="h-10 rounded-md border border-input bg-background px-3 text-sm" defaultValue={filters.estado ?? ""} id="estado" name="estado">
          <option value="">Todos</option>
          {estadoOptions.map((state) => <option key={state} value={state}>{state}</option>)}
        </select>
      </div>
      <button className="h-10 rounded-md bg-primary px-4 text-sm font-semibold text-primary-foreground" type="submit">Consultar</button>
    </form>
  );
}

export function ConfiguracoesFinanceiras({ actions, filters, permissions, recoveryHref, configuracoes, vigente, modalidades, calendarios }: ConfiguracoesProps) {
  const commandPermissions: readonly ConfiguracaoPermission[] = [
    CONFIGURACOES_MANAGE_PERMISSION,
    CONFIGURACOES_APPROVE_PERMISSION,
    CONFIGURACOES_ACTIVATE_PERMISSION,
    MODALIDADE_MANAGE_PERMISSION,
    CALENDARIO_MANAGE_PERMISSION,
    SNAPSHOT_CAPTURE_PERMISSION,
  ];
  const canCommand = commandPermissions.some((permission) => hasExactPermission(permissions, permission));
  return (
    <div className="grid min-w-0 gap-6">
      <header className="grid gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">Configuracoes Financeiras</p>
          <h1 className="text-balance text-3xl font-bold tracking-tight">Configuracoes Financeiras</h1>
          <p className="mt-2 max-w-3xl text-sm text-muted-foreground">Gerencie modalidades, calendarios e regras financeiras usadas pela operacao. As contas finais continuam sendo validadas pelo sistema.</p>
          <p className="sr-only">Estados cobertos: loading empty denied 400 403 404 409 422 500 overflow.</p>
        </div>
        <Filters filters={filters} />
      </header>
      {canCommand ? <ConfiguracoesActions {...actions} /> : <DeniedState />}
      <div className="grid min-w-0 gap-5 xl:grid-cols-2">
        <Suspense fallback={<ConfiguracoesLoadingState title="Configuracoes cadastradas" />}><ConfiguracoesSection recoveryHref={recoveryHref} result={configuracoes} /></Suspense>
        <Suspense fallback={<ConfiguracoesLoadingState title="Configuracao vigente" />}><VigenteSection recoveryHref={recoveryHref} result={vigente} /></Suspense>
        <Suspense fallback={<ConfiguracoesLoadingState title="Modalidades" />}><ModalidadesSection recoveryHref={recoveryHref} result={modalidades} /></Suspense>
        <Suspense fallback={<ConfiguracoesLoadingState title="Calendarios" />}><CalendariosSection recoveryHref={recoveryHref} result={calendarios} /></Suspense>
      </div>
    </div>
  );
}
