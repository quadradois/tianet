import Link from "next/link";
import { redirect } from "next/navigation";
import type { ReactNode } from "react";

import type { Devedor, DevedorActionState, DevedorHistory, DevedoresList, DevedoresProblem, DevedoresReadResult } from "../../lib/devedores/devedores-policy";
import { hasAnyComercialPermission } from "../../lib/comercial/comercial-policy";
import {
  DEVEDOR_CREATE_PERMISSION,
  DEVEDOR_INACTIVATE_PERMISSION,
  DEVEDOR_REACTIVATE_PERMISSION,
  DEVEDOR_UPDATE_PERMISSION,
  hasExactPermission,
} from "../../lib/devedores/devedores-policy";
import { Alert, AlertDescription, AlertTitle } from "../ui/alert";
import { Button } from "../ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/card";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import { Skeleton } from "../ui/skeleton";

import { DevedorForm } from "./devedor-form.client";
import { DevedorStatusDialog } from "./devedor-status-dialog.client";

const DATE_TIME_FORMATTER = new Intl.DateTimeFormat("pt-BR", {
  dateStyle: "short",
  timeStyle: "short",
  timeZone: "America/Sao_Paulo",
});

type Action = (state: DevedorActionState, formData: FormData) => Promise<DevedorActionState>;

type DevedoresPageProps = Readonly<{
  createAction: Action;
  filters: Readonly<{ documento?: string; estado?: "ativo" | "inativo"; nome?: string }>;
  initialState: DevedorActionState;
  permissions: readonly string[];
  recoveryHref: string;
  result: DevedoresReadResult<DevedoresList | Devedor>;
}>;

type DetailProps = Readonly<{
  devedor: DevedoresReadResult<Devedor>;
  history: DevedoresReadResult<DevedorHistory>;
  initialState: DevedorActionState;
  inactivateAction: Action;
  permissions: readonly string[];
  reactivateAction: Action;
  recoveryHref: string;
  updateAction: Action;
}>;

export function DevedoresLoadingState() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Devedores</CardTitle>
        <CardDescription>loading dados cadastrais oficiais...</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-3" role="status" aria-label="loading Devedores">
        <Skeleton className="h-8 w-1/3" />
        <Skeleton className="h-32 w-full" />
      </CardContent>
    </Card>
  );
}

function ProblemState({ problem }: Readonly<{ problem: DevedoresProblem }>) {
  const neutral404 = problem.status === 404;
  return (
    <Alert role="alert" variant="danger">
      <AlertTitle>{neutral404 ? "Devedor nao encontrado ou indisponivel (404)" : `Erro ${problem.status}`}</AlertTitle>
      <AlertDescription>
        {neutral404 ? "Devedor nao encontrado ou indisponivel." : problem.mensagem} Correlation ID: {problem.correlationId}
      </AlertDescription>
    </Alert>
  );
}

function DeniedState({ children = "Voce nao possui permissao para esta acao." }: Readonly<{ children?: ReactNode }>) {
  return <Alert><AlertTitle>denied</AlertTitle><AlertDescription>{children}</AlertDescription></Alert>;
}

function SectionResult<T>({ result, recoveryHref, children }: Readonly<{
  result: DevedoresReadResult<T>;
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

function formatDateTime(value: string): string {
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : DATE_TIME_FORMATTER.format(parsed);
}

function DevedorSummary({ devedor }: Readonly<{ devedor: Devedor }>) {
  return (
    <dl className="grid gap-2 text-sm sm:grid-cols-2">
      <div><dt className="text-muted-foreground">Documento</dt><dd className="break-words font-semibold">{devedor.documento}</dd></div>
      <div><dt className="text-muted-foreground">Estado</dt><dd>{devedor.estado}</dd></div>
      <div><dt className="text-muted-foreground">Criado em</dt><dd><time dateTime={devedor.criado_em}>{formatDateTime(devedor.criado_em)}</time></dd></div>
      <div><dt className="text-muted-foreground">Atualizado em</dt><dd>{devedor.atualizado_em ? <time dateTime={devedor.atualizado_em}>{formatDateTime(devedor.atualizado_em)}</time> : "Nao informado"}</dd></div>
    </dl>
  );
}

function DevedoresTable({ list }: Readonly<{ list: DevedoresList }>) {
  if (list.items.length === 0) return <p role="status">empty: nenhum Devedor foi retornado para a Carteira corrente.</p>;
  return (
    <div aria-label="Tabela de Devedores com overflow" className="overflow-x-auto rounded-md border" role="region" tabIndex={0}>
      <table className="w-full min-w-[48rem] text-left text-sm">
        <caption className="sr-only">Devedores da Carteira corrente</caption>
        <thead className="bg-muted">
          <tr><th className="p-2">Nome</th><th className="p-2">Documento</th><th className="p-2">Estado</th><th className="p-2">Contato</th><th className="p-2">Detalhe</th></tr>
        </thead>
        <tbody>
          {list.items.map((item) => (
            <tr className="border-t" key={item.id}>
              <td className="break-words p-2 font-semibold">{item.nome}</td>
              <td className="break-words p-2">{item.documento}</td>
              <td className="p-2">{item.estado}</td>
              <td className="break-words p-2">{item.contatos[0]?.valor ?? "Sem contato"}</td>
              <td className="p-2"><Link className="font-semibold text-primary underline-offset-4 hover:underline" href={`/app/devedores/${item.id}`}>Consultar</Link></td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="px-2 py-3 text-xs text-muted-foreground">Total oficial: <span className="tabular-nums">{list.total}</span> | pagina {list.page} de {list.pages}</p>
    </div>
  );
}

function SearchForm({ filters }: Readonly<{ filters: DevedoresPageProps["filters"] }>) {
  return (
    <form className="grid gap-3 rounded-lg border bg-card p-4 md:grid-cols-[1fr_1fr_10rem_auto]" method="get">
      <div className="grid gap-2">
        <Label htmlFor="nome">Nome</Label>
        <Input defaultValue={filters.nome ?? ""} id="nome" maxLength={200} name="nome" placeholder="Nome parcial" />
      </div>
      <div className="grid gap-2">
        <Label htmlFor="documento">Documento</Label>
        <Input defaultValue={filters.documento ?? ""} id="documento" maxLength={20} name="documento" placeholder="Consulta exata" />
      </div>
      <div className="grid gap-2">
        <Label htmlFor="estado">Estado</Label>
        <select className="min-h-(--size-control) rounded-md border bg-background px-3 text-sm" defaultValue={filters.estado ?? ""} id="estado" name="estado">
          <option value="">Todos</option>
          <option value="ativo">Ativo</option>
          <option value="inativo">Inativo</option>
        </select>
      </div>
      <Button className="self-end" type="submit">Filtrar</Button>
    </form>
  );
}

export function DevedoresPage({ createAction, filters, initialState, permissions, recoveryHref, result }: DevedoresPageProps) {
  const canCreate = hasExactPermission(permissions, DEVEDOR_CREATE_PERMISSION);
  return (
    <div className="grid min-w-0 gap-6">
      <header>
        <p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">Cadastro</p>
        <h1 className="text-balance text-3xl font-bold tracking-tight">Devedores</h1>
        <p className="mt-2 max-w-3xl text-sm text-muted-foreground">Jornada P0 de Devedores da Carteira corrente. O backend permanece autoridade dos dados cadastrais e dos conflitos.</p>
      </header>
      <SearchForm filters={filters} />
      <SectionResult result={result} recoveryHref={recoveryHref}>
        {(data) => "items" in data ? <DevedoresTable list={data} /> : (
          <Card>
            <CardHeader><CardTitle>Resultado por documento</CardTitle><CardDescription>Consulta exata pelo documento informado.</CardDescription></CardHeader>
            <CardContent className="grid gap-3"><h2 className="text-xl font-semibold">{data.nome}</h2><DevedorSummary devedor={data} /><Button asChild variant="outline"><Link href={`/app/devedores/${data.id}`}>Abrir detalhe</Link></Button></CardContent>
          </Card>
        )}
      </SectionResult>
      {canCreate ? <DevedorForm action={createAction} initialState={initialState} mode="create" /> : <DeniedState>Sem permissao de criar Devedor.</DeniedState>}
    </div>
  );
}

function HistoryView({ history }: Readonly<{ history: DevedorHistory }>) {
  if (history.eventos.length === 0) return <p role="status">empty: nenhum evento de historico retornado.</p>;
  return (
    <ol className="grid gap-2">
      {history.eventos.map((event) => (
        <li className="rounded-md border p-3" key={`${event.acao}-${event.status}-${event.criado_em}`}>
          <p className="font-semibold">{event.acao} | {event.status}</p>
          <p className="text-sm text-muted-foreground"><time dateTime={event.criado_em}>{formatDateTime(event.criado_em)}</time></p>
          {event.detalhes ? <p className="mt-1 break-words text-sm">{event.detalhes}</p> : null}
        </li>
      ))}
    </ol>
  );
}

export function DevedorDetailPage({ devedor, history, initialState, inactivateAction, permissions, reactivateAction, recoveryHref, updateAction }: DetailProps) {
  const canUpdate = hasExactPermission(permissions, DEVEDOR_UPDATE_PERMISSION);
  const canInactivate = hasExactPermission(permissions, DEVEDOR_INACTIVATE_PERMISSION);
  const canReactivate = hasExactPermission(permissions, DEVEDOR_REACTIVATE_PERMISSION);
  const canOpenCommercial = hasAnyComercialPermission(permissions);
  return (
    <div className="grid min-w-0 gap-6">
      <Link className="text-sm font-semibold text-primary underline-offset-4 hover:underline" href="/app/devedores">Voltar para Devedores</Link>
      <SectionResult result={devedor} recoveryHref={recoveryHref}>
        {(item) => (
          <>
            <Card>
              <CardHeader><CardTitle>{item.nome}</CardTitle><CardDescription>Detalhe cadastral oficial do Devedor.</CardDescription></CardHeader>
              <CardContent className="grid gap-4">
                <DevedorSummary devedor={item} />
                {canOpenCommercial && item.estado === "ativo"
                  ? <Button asChild variant="outline"><Link href={`/app/devedores/${item.id}/comercial`}>Abrir Comercial deste Devedor</Link></Button>
                  : null}
              </CardContent>
            </Card>
            {canUpdate ? <DevedorForm action={updateAction} devedor={item} initialState={initialState} mode="update" /> : <DeniedState>Sem permissao de atualizar Devedor.</DeniedState>}
            <div className="grid gap-4 md:grid-cols-2">
              {canInactivate ? <DevedorStatusDialog action={inactivateAction} devedor={item} initialState={initialState} operation="inativar" /> : <DeniedState>Sem permissao de inativar Devedor.</DeniedState>}
              {canReactivate ? <DevedorStatusDialog action={reactivateAction} devedor={item} initialState={initialState} operation="reativar" /> : <DeniedState>Sem permissao de reativar Devedor.</DeniedState>}
            </div>
          </>
        )}
      </SectionResult>
      <Card>
        <CardHeader><CardTitle>Historico cadastral</CardTitle><CardDescription>Eventos oficiais retornados pelo backend.</CardDescription></CardHeader>
        <CardContent><SectionResult result={history} recoveryHref={recoveryHref}>{(data) => <HistoryView history={data} />}</SectionResult></CardContent>
      </Card>
    </div>
  );
}
