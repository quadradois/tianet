import { redirect } from "next/navigation";
import type { ReactNode } from "react";

import {
  formatPerfilState,
  hasExactIamPermission,
  PERFIL_MANAGE_PERMISSION,
  PERFIL_READ_PERMISSION,
  type IamFilters,
  type IamProblem,
  type IamReadResult,
  type Perfil,
  type PermissoesCatalogo,
  type PermissoesEfetivas,
} from "../../lib/iam/iam-policy";
import { Alert, AlertDescription, AlertTitle } from "../ui/alert";
import { Button } from "../ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/card";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import { Skeleton } from "../ui/skeleton";

import { IamActions, type IamActionsProps } from "./iam-actions.client";

export type IamAdminProps = Readonly<{
  actions: IamActionsProps;
  catalogo: Promise<IamReadResult<PermissoesCatalogo>>;
  filters: IamFilters;
  perfil: Promise<IamReadResult<Perfil | null>>;
  perfis: Promise<IamReadResult<readonly Perfil[]>>;
  permissions: readonly string[];
  recoveryHref: string;
  usuarioPermissoes: Promise<IamReadResult<PermissoesEfetivas | null>>;
}>;

export function IamLoadingState() {
  return (
    <Card className="min-w-0">
      <CardHeader>
        <CardTitle>Acessos e permissoes</CardTitle>
        <CardDescription>Carregando perfis e permissoes...</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-3" role="status" aria-label="loading IAM">
        <Skeleton className="h-8 w-1/3" />
        <Skeleton className="h-40 w-full" />
      </CardContent>
    </Card>
  );
}

export function IamProblemState({ problem }: Readonly<{ problem: IamProblem }>) {
  const neutral404 = problem.status === 404;
  return (
    <Alert role="alert" variant="danger">
      <AlertTitle>{neutral404 ? "Recurso de acesso nao encontrado" : `Erro ${problem.status}`}</AlertTitle>
      <AlertDescription>
        {neutral404 ? "Recurso de acesso nao encontrado ou indisponivel." : problem.mensagem} Correlation ID: {problem.correlationId}
      </AlertDescription>
    </Alert>
  );
}

function DeniedState({ children = "Voce nao possui permissao para gerenciar acessos." }: Readonly<{ children?: ReactNode }>) {
  return <Alert><AlertTitle>Sem permissao</AlertTitle><AlertDescription>{children}</AlertDescription></Alert>;
}

function SectionResult<T>({ result, recoveryHref, children }: Readonly<{
  result: IamReadResult<T>;
  recoveryHref: string;
  children(data: T): ReactNode;
}>) {
  if (result.kind === "denied") return <DeniedState />;
  if (result.kind === "problem") {
    if (result.problem.status === 401) redirect(recoveryHref);
    return <IamProblemState problem={result.problem} />;
  }
  return children(result.data);
}

function PerfilList({ perfis }: Readonly<{ perfis: readonly Perfil[] }>) {
  if (perfis.length === 0) return <p role="status">Nenhum perfil encontrado.</p>;
  return (
    <div aria-label="Perfis IAM com overflow" className="overflow-x-auto rounded-md border" role="region" tabIndex={0}>
      <table className="w-full min-w-[54rem] text-left text-sm">
        <caption className="sr-only">Perfis de acesso</caption>
        <thead className="bg-muted">
          <tr><th className="p-2">Perfil</th><th className="p-2">Estado</th><th className="p-2">Permissoes</th><th className="p-2">Detalhe</th></tr>
        </thead>
        <tbody>
          {perfis.map((perfil) => (
            <tr className="border-t" key={perfil.id}>
              <td className="break-words p-2 font-semibold">{perfil.nome}<span className="block text-xs text-muted-foreground">ID {perfil.id}</span></td>
              <td className="p-2">{formatPerfilState(perfil.estado)}</td>
              <td className="break-words p-2">{perfil.permissoes.join(", ") || "Sem permissoes"}</td>
              <td className="p-2"><a className="font-semibold text-primary underline-offset-4 hover:underline" href={`/app/iam?perfil_id=${perfil.id}`}>Consultar</a></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function CatalogoView({ catalogo }: Readonly<{ catalogo: PermissoesCatalogo }>) {
  return (
    <Card className="min-w-0">
      <CardHeader><CardTitle>Catalogo de permissoes</CardTitle><CardDescription>Versao {catalogo.versao}. Use estes codigos para montar perfis.</CardDescription></CardHeader>
      <CardContent>
        <div aria-label="Catalogo de Permissoes com overflow" className="max-h-80 overflow-auto rounded-md border" role="region" tabIndex={0}>
          <ul className="grid min-w-[36rem] gap-2 p-3 text-sm">
            {catalogo.itens.map((item) => (
              <li className="rounded-md border p-2" key={item.codigo}>
                <span className="font-semibold">{item.codigo}</span>
                <span className="ml-2 text-xs text-muted-foreground">{item.grupo}</span>
                <p className="break-words text-muted-foreground">{item.descricao}</p>
              </li>
            ))}
          </ul>
        </div>
      </CardContent>
    </Card>
  );
}

function PerfilDetail({ perfil }: Readonly<{ perfil: Perfil | null }>) {
  if (!perfil) return <p role="status">Informe um ID de perfil para consultar detalhes.</p>;
  return (
    <Card className="min-w-0">
      <CardHeader><CardTitle>{perfil.nome}</CardTitle><CardDescription>Perfil da carteira atual.</CardDescription></CardHeader>
      <CardContent className="grid gap-2 text-sm">
        <p>ID: <span className="font-mono">{perfil.id}</span></p>
        <p>Estado: {perfil.estado}</p>
        <p className="break-words">Permissoes: {perfil.permissoes.join(", ") || "Sem permissoes"}</p>
      </CardContent>
    </Card>
  );
}

function UsuarioPermissoes({ value }: Readonly<{ value: PermissoesEfetivas | null }>) {
  if (!value) return <p role="status">Informe um ID de usuario para consultar permissoes efetivas.</p>;
  return (
    <Card>
      <CardHeader><CardTitle>Permissoes efetivas</CardTitle><CardDescription>Usuario {value.usuario_id}</CardDescription></CardHeader>
      <CardContent className="grid gap-2 text-sm">
        <p>Perfil: {value.perfil_nome ?? "Sem Perfil"} {value.perfil_id ? <span className="font-mono">({value.perfil_id})</span> : null}</p>
        <p className="break-words">Permissoes: {value.permissoes.join(", ") || "Sem permissoes efetivas"}</p>
      </CardContent>
    </Card>
  );
}

function FilterForm({ filters }: Readonly<{ filters: IamFilters }>) {
  return (
    <form className="grid gap-3 rounded-lg border bg-card p-4 md:grid-cols-[1fr_1fr_auto]" method="get">
      <div className="grid gap-2">
        <Label htmlFor="iam-filter-perfil">ID do perfil</Label>
        <Input defaultValue={filters.perfilId ?? ""} id="iam-filter-perfil" name="perfil_id" placeholder="ID do perfil" />
      </div>
      <div className="grid gap-2">
        <Label htmlFor="iam-filter-usuario">ID do usuario</Label>
        <Input defaultValue={filters.usuarioId ?? ""} id="iam-filter-usuario" name="usuario_id" placeholder="ID do usuario" />
      </div>
      <Button className="self-end" type="submit">Consultar acessos</Button>
    </form>
  );
}

export async function IamAdmin({ actions, catalogo, filters, perfil, perfis, permissions, recoveryHref, usuarioPermissoes }: IamAdminProps) {
  const canRead = hasExactIamPermission(permissions, PERFIL_READ_PERMISSION);
  const canManage = hasExactIamPermission(permissions, PERFIL_MANAGE_PERMISSION);
  const [perfisResult, catalogoResult, perfilResult, usuarioResult] = await Promise.all([perfis, catalogo, perfil, usuarioPermissoes]);
  return (
    <div className="grid min-w-0 gap-6">
      <header>
        <p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">Acessos</p>
        <h1 className="text-balance text-3xl font-bold tracking-tight">Perfis e permissoes</h1>
        <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
          Consulte perfis, veja permissoes e faca ajustes de acesso quando necessario.
        </p>
      </header>
      <FilterForm filters={filters} />
      {!canRead ? <DeniedState>Sem permissao para consultar acessos.</DeniedState> : null}
      <div className="grid min-w-0 gap-5 xl:grid-cols-2">
        <Card className="min-w-0">
          <CardHeader><CardTitle>Perfis</CardTitle><CardDescription>Perfis disponiveis nesta operacao.</CardDescription></CardHeader>
          <CardContent><SectionResult result={perfisResult} recoveryHref={recoveryHref}>{(data) => <PerfilList perfis={data} />}</SectionResult></CardContent>
        </Card>
        <SectionResult result={catalogoResult} recoveryHref={recoveryHref}>{(data) => <CatalogoView catalogo={data} />}</SectionResult>
        <SectionResult result={perfilResult} recoveryHref={recoveryHref}>{(data) => <PerfilDetail perfil={data} />}</SectionResult>
        <SectionResult result={usuarioResult} recoveryHref={recoveryHref}>{(data) => <UsuarioPermissoes value={data} />}</SectionResult>
      </div>
      {canManage ? <IamActions {...actions} /> : <DeniedState>Sem permissao para alterar perfis.</DeniedState>}
    </div>
  );
}
