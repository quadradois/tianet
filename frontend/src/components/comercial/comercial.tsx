import Link from "next/link";
import { redirect } from "next/navigation";
import type { ReactNode } from "react";

import {
  allowedProposalDecisions,
  COMERCIAL_PROPOSAL_CREATE_PERMISSION,
  COMERCIAL_PROPOSAL_INTEGRATE_PERMISSION,
  COMERCIAL_SIMULATION_CREATE_PERMISSION,
  hasExactPermission,
  type ApprovedProposalContract,
  type ComercialActionState,
  type ComercialProblem,
  type ComercialReadResult,
  type Proposal,
  type ProposalFilters,
  type ProposalList,
  type Simulation,
} from "../../lib/comercial/comercial-policy";
import { Alert, AlertDescription, AlertTitle } from "../ui/alert";
import { Button } from "../ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/card";
import { Label } from "../ui/label";
import { Skeleton } from "../ui/skeleton";

import { ComercialJsonForm } from "./comercial-json-form.client";
import { PropostaDecisionDialog } from "./proposta-decision-dialog.client";

const DATE_TIME_FORMATTER = new Intl.DateTimeFormat("pt-BR", {
  dateStyle: "short",
  timeStyle: "short",
  timeZone: "America/Sao_Paulo",
});

type Action = (state: ComercialActionState, formData: FormData) => Promise<ComercialActionState>;

type ComercialDevedorPageProps = Readonly<{
  createProposalAction: Action;
  createSimulationAction: Action;
  devedorId: string;
  filters: ProposalFilters;
  initialState: ComercialActionState;
  permissions: readonly string[];
  proposals: ComercialReadResult<ProposalList>;
  recoveryHref: string;
}>;

type PropostaPageProps = Readonly<{
  contract: ComercialReadResult<ApprovedProposalContract>;
  decisionAction: Action;
  initialState: ComercialActionState;
  permissions: readonly string[];
  proposal: ComercialReadResult<Proposal>;
  recoveryHref: string;
  simulation: ComercialReadResult<Simulation>;
  updateAction: Action;
}>;

export function ComercialLoadingState() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Comercial</CardTitle>
        <CardDescription>loading simulações e propostas oficiais...</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-3" role="status" aria-label="loading Comercial">
        <Skeleton className="h-8 w-1/3" />
        <Skeleton className="h-40 w-full" />
      </CardContent>
    </Card>
  );
}

function ProblemState({ problem }: Readonly<{ problem: ComercialProblem }>) {
  const neutral404 = problem.status === 404;
  return (
    <Alert role="alert" variant="danger">
      <AlertTitle>{neutral404 ? "Recurso comercial nao encontrado ou indisponivel (404)" : `Erro ${problem.status}`}</AlertTitle>
      <AlertDescription>
        {neutral404 ? "Recurso comercial nao encontrado ou indisponivel." : problem.mensagem} Correlation ID: {problem.correlationId}
      </AlertDescription>
    </Alert>
  );
}

function DeniedState({ children = "denied: voce nao possui permissao para esta acao comercial." }: Readonly<{ children?: ReactNode }>) {
  return <Alert><AlertTitle>denied</AlertTitle><AlertDescription>{children}</AlertDescription></Alert>;
}

function SectionResult<T>({ result, recoveryHref, children }: Readonly<{
  result: ComercialReadResult<T>;
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

function ProposalTable({ proposals }: Readonly<{ proposals: ProposalList }>) {
  if (proposals.items.length === 0) return <p role="status">empty: nenhuma proposta comercial retornada para este Devedor.</p>;
  return (
    <div aria-label="Tabela de propostas comerciais com overflow" className="overflow-x-auto rounded-md border" role="region" tabIndex={0}>
      <table className="w-full min-w-[56rem] text-left text-sm">
        <caption className="sr-only">Propostas comerciais do Devedor ativo</caption>
        <thead className="bg-muted">
          <tr><th className="p-2">Proposta</th><th className="p-2">Estado</th><th className="p-2">Simulacao</th><th className="p-2">Decisoes</th><th className="p-2">Criada em</th><th className="p-2">Detalhe</th></tr>
        </thead>
        <tbody>
          {proposals.items.map((proposal) => (
            <tr className="border-t" key={proposal.id}>
              <td className="break-all p-2 font-semibold">{proposal.id}</td>
              <td className="p-2">{proposal.estado}</td>
              <td className="break-all p-2">{proposal.simulacao_id ?? "Sem simulacao vinculada"}</td>
              <td className="p-2 tabular-nums">{proposal.total_decisoes}</td>
              <td className="p-2"><time dateTime={proposal.criado_em}>{formatDateTime(proposal.criado_em)}</time></td>
              <td className="p-2"><Link className="font-semibold text-primary underline-offset-4 hover:underline" href={`/app/comercial/propostas/${proposal.id}`}>Consultar</Link></td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="px-2 py-3 text-xs text-muted-foreground">Total oficial: <span className="tabular-nums">{proposals.total}</span> | pagina {proposals.page} de {proposals.pages}</p>
    </div>
  );
}

function ProposalFilter({ filters }: Readonly<{ filters: ProposalFilters }>) {
  return (
    <form className="grid gap-3 rounded-lg border bg-card p-4 md:grid-cols-[12rem_8rem_auto]" method="get">
      <div className="grid gap-2">
        <Label htmlFor="estado">Estado</Label>
        <select className="min-h-(--size-control) rounded-md border bg-background px-3 text-sm" defaultValue={filters.estado ?? ""} id="estado" name="estado">
          <option value="">Todos</option>
          <option value="rascunho">Rascunho</option>
          <option value="em_analise">Em analise</option>
          <option value="aprovada">Aprovada</option>
          <option value="recusada">Recusada</option>
          <option value="cancelada">Cancelada</option>
          <option value="expirada">Expirada</option>
        </select>
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

function ProposalSummary({ proposal }: Readonly<{ proposal: Proposal }>) {
  return (
    <dl className="grid gap-2 text-sm sm:grid-cols-2">
      <div><dt className="text-muted-foreground">Proposta</dt><dd className="break-all font-semibold">{proposal.id}</dd></div>
      <div><dt className="text-muted-foreground">Estado</dt><dd>{proposal.estado}</dd></div>
      <div><dt className="text-muted-foreground">Devedor</dt><dd className="break-all">{proposal.devedor_id}</dd></div>
      <div><dt className="text-muted-foreground">Simulacao</dt><dd className="break-all">{proposal.simulacao_id ?? "Sem simulacao vinculada"}</dd></div>
      <div><dt className="text-muted-foreground">Criada em</dt><dd><time dateTime={proposal.criado_em}>{formatDateTime(proposal.criado_em)}</time></dd></div>
      <div><dt className="text-muted-foreground">Total de decisoes</dt><dd className="tabular-nums">{proposal.total_decisoes}</dd></div>
    </dl>
  );
}

export function ComercialDevedorPage({ createProposalAction, createSimulationAction, devedorId, filters, initialState, permissions, proposals, recoveryHref }: ComercialDevedorPageProps) {
  const canSimulate = hasExactPermission(permissions, COMERCIAL_SIMULATION_CREATE_PERMISSION);
  const canCreateProposal = hasExactPermission(permissions, COMERCIAL_PROPOSAL_CREATE_PERMISSION);
  return (
    <div className="grid min-w-0 gap-6">
      <Link className="text-sm font-semibold text-primary underline-offset-4 hover:underline" href={`/app/devedores/${devedorId}`}>Voltar para o Devedor</Link>
      <header>
        <p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">Comercial</p>
        <h1 className="text-balance text-3xl font-bold tracking-tight">Simulacoes e propostas</h1>
        <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
          Jornada P0 a partir de Devedor ativo. Parametros sao tratados como retorno oficial e opaco do backend; o frontend nao calcula valores financeiros.
        </p>
      </header>
      <ProposalFilter filters={filters} />
      <SectionResult result={proposals} recoveryHref={recoveryHref}>
        {(data) => <ProposalTable proposals={data} />}
      </SectionResult>
      <div className="grid gap-4 lg:grid-cols-2">
        {canSimulate ? <ComercialJsonForm action={createSimulationAction} devedorId={devedorId} initialState={initialState} mode="simulation" /> : <DeniedState>Sem permissao para criar simulacao comercial.</DeniedState>}
        {canCreateProposal ? <ComercialJsonForm action={createProposalAction} devedorId={devedorId} initialState={initialState} mode="proposal" /> : <DeniedState>Sem permissao para criar proposta comercial.</DeniedState>}
      </div>
    </div>
  );
}

export function PropostaComercialPage({ contract, decisionAction, initialState, permissions, proposal, recoveryHref, simulation, updateAction }: PropostaPageProps) {
  const canCreate = hasExactPermission(permissions, COMERCIAL_PROPOSAL_CREATE_PERMISSION);
  const canIntegrate = hasExactPermission(permissions, COMERCIAL_PROPOSAL_INTEGRATE_PERMISSION);
  return (
    <div className="grid min-w-0 gap-6">
      <Link className="text-sm font-semibold text-primary underline-offset-4 hover:underline" href="/app/devedores">Voltar para Devedores</Link>
      <SectionResult result={proposal} recoveryHref={recoveryHref}>
        {(item) => (
          <>
            <Card>
              <CardHeader>
                <CardTitle>Proposta comercial</CardTitle>
                <CardDescription>Detalhe oficial retornado pelo backend Comercial.</CardDescription>
              </CardHeader>
              <CardContent className="grid gap-4">
                <ProposalSummary proposal={item} />
                <JsonBlock title="Parametros comerciais retornados" value={item.parametros} />
              </CardContent>
            </Card>
            {canCreate && item.estado === "rascunho"
              ? <ComercialJsonForm action={updateAction} initialState={initialState} mode="proposal-update" propostaId={item.id} />
              : <DeniedState>Edicao indisponivel para este estado ou permissao.</DeniedState>}
            <Card>
              <CardHeader>
                <CardTitle>Decisoes comerciais</CardTitle>
                <CardDescription>Acoes aparecem conforme estado retornado e permissao de decisao.</CardDescription>
              </CardHeader>
              <CardContent className="flex flex-wrap gap-3">
                {allowedProposalDecisions(item, permissions).length === 0 ? <DeniedState>Nenhuma decisao comercial disponivel.</DeniedState> : null}
                {allowedProposalDecisions(item, permissions).map((decision) => (
                  <PropostaDecisionDialog action={decisionAction} decision={decision as "enviar-para-analise" | "aprovar" | "recusar" | "cancelar" | "expirar"} initialState={initialState} key={decision} proposal={item} />
                ))}
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Simulacao comercial vinculada</CardTitle>
                <CardDescription>Consulta read-only da simulacao oficial quando a Proposta informa `simulacao_id`.</CardDescription>
              </CardHeader>
              <CardContent>
                {item.simulacao_id ? (
                  <SectionResult result={simulation} recoveryHref={recoveryHref}>
                    {(data) => <JsonBlock title="parametros da simulacao" value={data.parametros} />}
                  </SectionResult>
                ) : <DeniedState>Proposta sem simulacao vinculada.</DeniedState>}
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Contrato logico</CardTitle>
                <CardDescription>Saida read-only para etapa futura; nao cria obrigacao financeira.</CardDescription>
              </CardHeader>
              <CardContent>
                {canIntegrate && item.estado === "aprovada" ? (
                  <SectionResult result={contract} recoveryHref={recoveryHref}>
                    {(data) => (
                      <div className="grid gap-4">
                        <JsonBlock title="contrato logico aprovado" value={data.parametros_aprovados} />
                        {permissions.includes("contratos.contrato.criar") ? (
                          <Button asChild>
                            <Link href={`/app/contratos?proposta_id=${item.id}`}>Formalizar contrato</Link>
                          </Button>
                        ) : <DeniedState>Sem permissao para formalizar contrato.</DeniedState>}
                      </div>
                    )}
                  </SectionResult>
                ) : <DeniedState>Contrato logico disponivel apenas para proposta aprovada e permissao de integracao.</DeniedState>}
              </CardContent>
            </Card>
          </>
        )}
      </SectionResult>
    </div>
  );
}
