import { redirect } from "next/navigation";
import type { ReactNode } from "react";

import {
  COBRANCA_ACTION_REGISTER_PERMISSION,
  COBRANCA_PROMISE_APPROPRIATE_PERMISSION,
  COBRANCA_PROMISE_REGISTER_PERMISSION,
  hasExactPermission,
  type CobrancaActionState,
  type CobrancaCase,
  type CobrancaFilters,
  type CobrancaProblem,
  type CobrancaQueue,
  type CobrancaReadResult,
} from "../../lib/cobranca/cobranca-policy";
import { moeda } from "../../lib/formato/brasileiro";
import { Alert, AlertDescription, AlertTitle } from "../ui/alert";
import { Button } from "../ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/card";
import { Label } from "../ui/label";
import { Skeleton } from "../ui/skeleton";

import { AppropriationForm, CobrancaActionForm, PromiseForm } from "./cobranca-command-dialog.client";

type Action = (state: CobrancaActionState, formData: FormData) => Promise<CobrancaActionState>;

type CobrancaPageProps = Readonly<{
  actionState: CobrancaActionState;
  appropriatePaymentAction: Action;
  filters: CobrancaFilters;
  permissions: readonly string[];
  registerAction: Action;
  registerPromiseAction: Action;
  recoveryHref: string;
  result: CobrancaReadResult<CobrancaQueue>;
}>;

const DATE_TIME_FORMATTER = new Intl.DateTimeFormat("pt-BR", {
  dateStyle: "short",
  timeStyle: "short",
  timeZone: "America/Sao_Paulo",
});

export function CobrancaLoadingState() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Cobranca</CardTitle>
        <CardDescription>Carregando fila de cobranca...</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-3" role="status" aria-label="loading Cobranca">
        <Skeleton className="h-8 w-1/3" />
        <Skeleton className="h-48 w-full" />
      </CardContent>
    </Card>
  );
}

function formatDateTime(value: string): string {
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : DATE_TIME_FORMATTER.format(parsed);
}

function ProblemState({ problem }: Readonly<{ problem: CobrancaProblem }>) {
  const neutral404 = problem.status === 404;
  return (
    <Alert role="alert" variant="danger">
      <AlertTitle>{neutral404 ? "Caso de cobranca nao encontrado ou indisponivel (404)" : `Erro ${problem.status}`}</AlertTitle>
      <AlertDescription>
        {neutral404 ? "Caso de cobranca nao encontrado ou indisponivel." : problem.mensagem} Correlation ID: {problem.correlationId}
      </AlertDescription>
    </Alert>
  );
}

function DeniedState({ children = "Voce nao possui permissao para operar Cobranca." }: Readonly<{ children?: ReactNode }>) {
  return <Alert><AlertTitle>Sem permissao</AlertTitle><AlertDescription>{children}</AlertDescription></Alert>;
}

function SectionResult<T>({ result, recoveryHref, children }: Readonly<{
  result: CobrancaReadResult<T>;
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

function FilterForm({ filters }: Readonly<{ filters: CobrancaFilters }>) {
  return (
    <form className="grid gap-3 rounded-lg border bg-card p-4 md:grid-cols-[13rem_1fr_auto]" method="get">
      <div className="grid gap-2">
        <Label htmlFor="estado">Estado</Label>
        <select className="min-h-(--size-control) rounded-md border bg-background px-3 text-sm" defaultValue={filters.estado ?? ""} id="estado" name="estado">
          <option value="">Ativos</option>
          <option value="pendente">Pendente</option>
          <option value="em_andamento">Em andamento</option>
          <option value="encerrado">Encerrado</option>
        </select>
      </div>
      <div className="grid gap-2">
        <Label htmlFor="devedor_id">Devedor</Label>
        <input className="min-h-(--size-control) rounded-md border bg-background px-3 text-sm" defaultValue={filters.devedorId ?? ""} id="devedor_id" name="devedor_id" placeholder="ID do devedor, se houver" />
      </div>
      <Button className="self-end" type="submit">Filtrar fila</Button>
    </form>
  );
}

function CaseSummary({ item }: Readonly<{ item: CobrancaCase }>) {
  return (
    <dl className="grid gap-2 text-sm md:grid-cols-2">
      <div><dt className="text-muted-foreground">Caso</dt><dd className="break-all font-semibold">{item.caso_id}</dd></div>
      <div><dt className="text-muted-foreground">Estado</dt><dd>{item.estado}</dd></div>
      <div><dt className="text-muted-foreground">Devedor</dt><dd className="break-all">{item.devedor_id}</dd></div>
      <div><dt className="text-muted-foreground">Emprestimo</dt><dd className="break-all">{item.emprestimo_id ?? "Nao vinculado"}</dd></div>
      <div><dt className="text-muted-foreground">Origem</dt><dd>{item.origem}</dd></div>
      <div><dt className="text-muted-foreground">Criado em</dt><dd><time dateTime={item.criado_em}>{formatDateTime(item.criado_em)}</time></dd></div>
      <div><dt className="text-muted-foreground">Pendente oficial</dt><dd className="tabular-nums">{moeda(item.total_pendente)}</dd></div>
    </dl>
  );
}

function CaseForms({ actionRegister, appropriatePromise, initialState, item, permissions, promiseRegister }: Readonly<{
  actionRegister: Action;
  appropriatePromise: Action;
  initialState: CobrancaActionState;
  item: CobrancaCase;
  permissions: readonly string[];
  promiseRegister: Action;
}>) {
  const canRegisterAction = hasExactPermission(permissions, COBRANCA_ACTION_REGISTER_PERMISSION);
  const canRegisterPromise = hasExactPermission(permissions, COBRANCA_PROMISE_REGISTER_PERMISSION);
  const canAppropriatePromise = hasExactPermission(permissions, COBRANCA_PROMISE_APPROPRIATE_PERMISSION);
  return (
    <div className="grid gap-4 lg:grid-cols-3">
      {canRegisterAction ? <CobrancaActionForm action={actionRegister} caseItem={item} initialState={initialState} /> : <DeniedState>Sem permissao para registrar acao de cobranca.</DeniedState>}
      {canRegisterPromise ? <PromiseForm action={promiseRegister} caseItem={item} initialState={initialState} /> : <DeniedState>Sem permissao para registrar promessa.</DeniedState>}
      {canAppropriatePromise ? <AppropriationForm action={appropriatePromise} caseItem={item} initialState={initialState} /> : <DeniedState>Sem permissao para apropriar promessa.</DeniedState>}
    </div>
  );
}

function QueueView({ actionState, appropriatePaymentAction, data, permissions, registerAction, registerPromiseAction }: Readonly<{
  actionState: CobrancaActionState;
  appropriatePaymentAction: Action;
  data: CobrancaQueue;
  permissions: readonly string[];
  registerAction: Action;
  registerPromiseAction: Action;
}>) {
  if (data.items.length === 0) return <p role="status">Nenhum caso ativo encontrado para esta carteira.</p>;
  return (
    <div className="grid gap-4">
      <h2 className="text-xl font-semibold">Casos de cobranca</h2>
      <p className="text-sm text-muted-foreground">Total: <span className="tabular-nums">{data.total}</span>. Saldos e promessas sao conferidos pelo sistema.</p>
      <div aria-label="Casos de cobranca" className="overflow-x-auto rounded-md border" data-state="overflow" role="region" tabIndex={0}>
        <table className="w-full min-w-[72rem] text-left text-sm">
          <caption className="sr-only">Fila de cobranca operacional</caption>
          <thead className="bg-muted">
            <tr><th className="p-2">Titulo</th><th className="p-2">Estado</th><th className="p-2">Pendente</th><th className="p-2">Caso</th><th className="p-2">Devedor</th><th className="p-2">Criado em</th></tr>
          </thead>
          <tbody>
            {data.items.map((item) => (
              <tr className="border-t" key={item.caso_id}>
                <td className="max-w-xs break-words p-2 font-semibold">{item.titulo}</td>
                <td className="p-2">{item.estado}</td>
                <td className="p-2 tabular-nums">{moeda(item.total_pendente)}</td>
                <td className="break-all p-2">{item.caso_id}</td>
                <td className="break-all p-2">{item.devedor_id}</td>
                <td className="p-2"><time dateTime={item.criado_em}>{formatDateTime(item.criado_em)}</time></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {data.items.slice(0, 2).map((item) => (
        <Card key={`detalhe-${item.caso_id}`}>
          <CardHeader>
            <CardTitle>{item.titulo}</CardTitle>
            <CardDescription>Use estes comandos para registrar contato, promessa ou conciliacao deste caso.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4">
            <CaseSummary item={item} />
            <CaseForms actionRegister={registerAction} appropriatePromise={appropriatePaymentAction} initialState={actionState} item={item} permissions={permissions} promiseRegister={registerPromiseAction} />
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

export function CobrancaPage({ actionState, appropriatePaymentAction, filters, permissions, recoveryHref, registerAction, registerPromiseAction, result }: CobrancaPageProps) {
  return (
    <div className="grid min-w-0 gap-6">
      <header>
        <p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">Cobranca</p>
        <h1 className="text-balance text-3xl font-bold tracking-tight">Fila de cobranca</h1>
        <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
          Acompanhe quem precisa de contato, registre combinados e mantenha a fila de cobranca em dia.
        </p>
      </header>
      <FilterForm filters={filters} />
      <SectionResult result={result} recoveryHref={recoveryHref}>
        {(data) => (
          <QueueView
            appropriatePaymentAction={appropriatePaymentAction}
            data={data}
            actionState={actionState}
            permissions={permissions}
            registerPromiseAction={registerPromiseAction}
            registerAction={registerAction}
          />
        )}
      </SectionResult>
    </div>
  );
}
