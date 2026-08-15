import Link from "next/link";
import { redirect } from "next/navigation";
import type { ReactNode } from "react";

import {
  allowedContractDecisions,
  CONTRATO_CREATE_PERMISSION,
  hasExactPermission,
  type Contract,
  type ContractEvent,
  type ContractFilters,
  type ContractList,
  type ContratoActionState,
  type ContratoProblem,
  type ContratoReadResult,
} from "../../lib/contratos/contratos-policy";
import { Alert, AlertDescription, AlertTitle } from "../ui/alert";
import { Button } from "../ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/card";
import { Label } from "../ui/label";
import { Skeleton } from "../ui/skeleton";

import { ContratoCreateForm, ContratoDecisionDialog } from "./contrato-decision-dialog.client";

const DATE_TIME_FORMATTER = new Intl.DateTimeFormat("pt-BR", {
  dateStyle: "short",
  timeStyle: "short",
  timeZone: "America/Sao_Paulo",
});

type Action = (state: ContratoActionState, formData: FormData) => Promise<ContratoActionState>;

export type ContratosPageProps = Readonly<{
  createAction: Action;
  filters: ContractFilters;
  initialProposalId?: string | undefined;
  initialState: ContratoActionState;
  permissions: readonly string[];
  recoveryHref: string;
  result: ContratoReadResult<ContractList>;
}>;

export type ContratoDetailPageProps = Readonly<{
  action: Action;
  contract: ContratoReadResult<Contract>;
  history: ContratoReadResult<readonly ContractEvent[]>;
  initialState: ContratoActionState;
  permissions: readonly string[];
  recoveryHref: string;
}>;

export function ContratosLoadingState() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Contratos</CardTitle>
        <CardDescription>loading contratos oficiais...</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-3" role="status" aria-label="loading Contratos">
        <Skeleton className="h-8 w-1/3" />
        <Skeleton className="h-40 w-full" />
      </CardContent>
    </Card>
  );
}

function formatDateTime(value: string | null): string {
  if (!value) return "Nao informado";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : DATE_TIME_FORMATTER.format(parsed);
}

function ProblemState({ problem }: Readonly<{ problem: ContratoProblem }>) {
  const neutral404 = problem.status === 404;
  return (
    <Alert role="alert" variant="danger">
      <AlertTitle>{neutral404 ? "Contrato nao encontrado ou indisponivel (404)" : `Erro ${problem.status}`}</AlertTitle>
      <AlertDescription>
        {neutral404 ? "Contrato nao encontrado ou indisponivel." : problem.mensagem} Correlation ID: {problem.correlationId}
      </AlertDescription>
    </Alert>
  );
}

function DeniedState({ children = "denied: voce nao possui permissao para esta acao contratual." }: Readonly<{ children?: ReactNode }>) {
  return <Alert><AlertTitle>denied</AlertTitle><AlertDescription>{children}</AlertDescription></Alert>;
}

function SectionResult<T>({ result, recoveryHref, children }: Readonly<{
  result: ContratoReadResult<T>;
  recoveryHref: string;
  children(data: T): ReactNode;
}>) {
  if (result.kind === "denied") return <DeniedState />;
  if (result.kind === "problem") {
    if (result.problem.status === 401) redirect(recoveryHref);
    return <ProblemState problem={result.problem} />;
  }
  return children(result.data);
}

function JsonBlock({ title, value }: Readonly<{ title: string; value: Record<string, unknown> }>) {
  return (
    <div className="grid gap-2">
      <h3 className="font-semibold">{title}</h3>
      <pre className="max-h-72 overflow-auto rounded-md border bg-muted p-3 text-xs" tabIndex={0}>
        {JSON.stringify(value, null, 2)}
      </pre>
    </div>
  );
}

function ContractFilter({ filters }: Readonly<{ filters: ContractFilters }>) {
  return (
    <form className="grid gap-3 rounded-lg border bg-card p-4 md:grid-cols-[12rem_12rem_8rem_auto]" method="get">
      <div className="grid gap-2">
        <Label htmlFor="estado">Estado</Label>
        <select className="min-h-(--size-control) rounded-md border bg-background px-3 text-sm" defaultValue={filters.estado ?? ""} id="estado" name="estado">
          <option value="">Todos</option>
          <option value="rascunho">Rascunho</option>
          <option value="formalizado">Formalizado</option>
          <option value="assinado">Assinado</option>
          <option value="liberado_para_motor">Liberado para Motor</option>
          <option value="cancelado">Cancelado</option>
          <option value="encerrado">Encerrado</option>
        </select>
      </div>
      <div className="grid gap-2">
        <Label htmlFor="devedor_id">Devedor opcional</Label>
        <input className="min-h-(--size-control) rounded-md border bg-background px-3 text-sm" defaultValue={filters.devedorId ?? ""} id="devedor_id" name="devedor_id" placeholder="UUID do Devedor" />
      </div>
      <div className="grid gap-2">
        <Label htmlFor="size">Tamanho</Label>
        <select className="min-h-(--size-control) rounded-md border bg-background px-3 text-sm" defaultValue={String(filters.size)} id="size" name="size">
          <option value="10">10</option>
          <option value="20">20</option>
          <option value="50">50</option>
        </select>
      </div>
      <Button className="self-end" type="submit">Filtrar</Button>
    </form>
  );
}

function ContractTable({ contracts }: Readonly<{ contracts: ContractList }>) {
  if (contracts.items.length === 0) return <p role="status">empty: nenhum contrato retornado para esta Carteira.</p>;
  return (
    <div aria-label="Tabela de contratos com overflow" className="overflow-x-auto rounded-md border" role="region" tabIndex={0}>
      <table className="w-full min-w-[64rem] text-left text-sm">
        <caption className="sr-only">Contratos da Carteira operacional</caption>
        <thead className="bg-muted">
          <tr><th className="p-2">Contrato</th><th className="p-2">Estado</th><th className="p-2">Proposta</th><th className="p-2">Devedor</th><th className="p-2">Eventos</th><th className="p-2">Criado em</th><th className="p-2">Detalhe</th></tr>
        </thead>
        <tbody>
          {contracts.items.map((contract) => (
            <tr className="border-t" key={contract.id}>
              <td className="break-all p-2 font-semibold">{contract.id}</td>
              <td className="p-2">{contract.estado}</td>
              <td className="break-all p-2">{contract.proposta_comercial_id}</td>
              <td className="break-all p-2">{contract.devedor_id}</td>
              <td className="p-2 tabular-nums">{contract.total_eventos}</td>
              <td className="p-2"><time dateTime={contract.criado_em}>{formatDateTime(contract.criado_em)}</time></td>
              <td className="p-2"><Link className="font-semibold text-primary underline-offset-4 hover:underline" href={`/app/contratos/${contract.id}`}>Consultar</Link></td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="px-2 py-3 text-xs text-muted-foreground">Total oficial: <span className="tabular-nums">{contracts.total}</span> | pagina {contracts.page} de {contracts.pages}</p>
    </div>
  );
}

function ContractSummary({ contract }: Readonly<{ contract: Contract }>) {
  return (
    <dl className="grid gap-2 text-sm sm:grid-cols-2">
      <div><dt className="text-muted-foreground">Contrato</dt><dd className="break-all font-semibold">{contract.id}</dd></div>
      <div><dt className="text-muted-foreground">Estado</dt><dd>{contract.estado}</dd></div>
      <div><dt className="text-muted-foreground">Proposta</dt><dd className="break-all">{contract.proposta_comercial_id}</dd></div>
      <div><dt className="text-muted-foreground">Devedor</dt><dd className="break-all">{contract.devedor_id}</dd></div>
      <div><dt className="text-muted-foreground">Criado em</dt><dd><time dateTime={contract.criado_em}>{formatDateTime(contract.criado_em)}</time></dd></div>
      <div><dt className="text-muted-foreground">Assinado em</dt><dd>{formatDateTime(contract.assinado_em)}</dd></div>
      <div><dt className="text-muted-foreground">Liberado em</dt><dd>{formatDateTime(contract.liberado_em)}</dd></div>
      <div><dt className="text-muted-foreground">Eventos</dt><dd className="tabular-nums">{contract.total_eventos}</dd></div>
      {contract.estado === "liberado_para_motor" ? (
        <div><dt className="text-muted-foreground">Motor</dt><dd><Link className="font-semibold text-primary underline-offset-4 hover:underline" href={`/app/motor?contrato_id=${contract.id}`}>Criar Emprestimo no Motor</Link></dd></div>
      ) : null}
    </dl>
  );
}

function HistoryList({ events }: Readonly<{ events: readonly ContractEvent[] }>) {
  if (events.length === 0) return <p role="status">empty: nenhum evento contratual retornado.</p>;
  return (
    <ol className="grid gap-3">
      {events.map((event) => (
        <li className="rounded-md border p-3" key={event.id}>
          <p className="font-semibold">{event.tipo}</p>
          <p className="text-sm text-muted-foreground">{event.estado_anterior} → {event.estado_posterior}</p>
          <p className="text-sm">Motivo: {event.motivo ?? "Nao informado"}</p>
          <p className="text-xs text-muted-foreground"><time dateTime={event.criado_em}>{formatDateTime(event.criado_em)}</time></p>
        </li>
      ))}
    </ol>
  );
}

export function ContratosPage({ createAction, filters, initialProposalId, initialState, permissions, recoveryHref, result }: ContratosPageProps) {
  const canCreate = hasExactPermission(permissions, CONTRATO_CREATE_PERMISSION);
  return (
    <div className="grid min-w-0 gap-6">
      <header>
        <p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">Contratos</p>
        <h1 className="text-balance text-3xl font-bold tracking-tight">Contratos de Credito</h1>
        <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
          Formalizacao P0 a partir de Proposta aprovada. Parametros permanecem opacos; liberar para Motor gera somente saida logica, sem Emprestimo ou Pagamento.
        </p>
      </header>
      <ContractFilter filters={filters} />
      {canCreate ? <ContratoCreateForm action={createAction} initialProposalId={initialProposalId} initialState={initialState} /> : <DeniedState>Sem permissao para formalizar contrato.</DeniedState>}
      <SectionResult result={result} recoveryHref={recoveryHref}>
        {(data) => <ContractTable contracts={data} />}
      </SectionResult>
    </div>
  );
}

export function ContratoDetailPage({ action, contract, history, initialState, permissions, recoveryHref }: ContratoDetailPageProps) {
  return (
    <div className="grid min-w-0 gap-6">
      <Link className="text-sm font-semibold text-primary underline-offset-4 hover:underline" href="/app/contratos">Voltar para Contratos</Link>
      <SectionResult result={contract} recoveryHref={recoveryHref}>
        {(item) => (
          <>
            <Card>
              <CardHeader>
                <CardTitle>Contrato de Credito</CardTitle>
                <CardDescription>Detalhe oficial retornado pelo backend de Contratos.</CardDescription>
              </CardHeader>
              <CardContent className="grid gap-4">
                <ContractSummary contract={item} />
                <JsonBlock title="Parametros contratados retornados" value={item.parametros} />
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Acoes contratuais</CardTitle>
                <CardDescription>Estados e transicoes pertencem ao backend. Liberar para Motor nao cria Emprestimo.</CardDescription>
              </CardHeader>
              <CardContent className="flex flex-wrap gap-3">
                {allowedContractDecisions(item, permissions).length === 0 ? <DeniedState>Nenhuma acao contratual disponivel.</DeniedState> : null}
                {allowedContractDecisions(item, permissions).map((decision) => (
                  <ContratoDecisionDialog action={action} contract={item} decision={decision} initialState={initialState} key={decision} />
                ))}
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Historico contratual</CardTitle>
                <CardDescription>Eventos append-only retornados pelo endpoint oficial.</CardDescription>
              </CardHeader>
              <CardContent>
                <SectionResult result={history} recoveryHref={recoveryHref}>
                  {(events) => <HistoryList events={events} />}
                </SectionResult>
              </CardContent>
            </Card>
          </>
        )}
      </SectionResult>
    </div>
  );
}
