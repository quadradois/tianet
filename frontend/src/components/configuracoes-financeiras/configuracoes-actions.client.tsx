"use client";

import { useActionState, type ReactNode } from "react";

import type { ConfiguracoesActionState } from "../../lib/configuracoes-financeiras/configuracoes-policy";

import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Label } from "../ui/label";

const initialState: ConfiguracoesActionState = { kind: "idle", message: "Aguardando envio." };
type Action = (state: ConfiguracoesActionState, formData: FormData) => Promise<ConfiguracoesActionState>;

export type ConfiguracoesActionsProps = Readonly<{
  activateAction: Action;
  approveAction: Action;
  captureSnapshotAction: Action;
  createCalendarioAction: Action;
  createConfiguracaoAction: Action;
  createModalidadeAction: Action;
  inactivateAction: Action;
  programAction: Action;
}>;

function ActionFeedback({ state }: Readonly<{ state: ConfiguracoesActionState }>) {
  if (state.kind === "idle") return <p className="text-xs text-muted-foreground">{state.message}</p>;
  return (
    <p className={state.kind === "success" ? "text-xs text-success" : "text-xs text-destructive"} role={state.kind === "problem" ? "alert" : "status"}>
      {state.message} Correlation ID: {state.correlationId}
    </p>
  );
}

function ActionForm({ action, button, children }: Readonly<{
  action: (state: ConfiguracoesActionState, formData: FormData) => Promise<ConfiguracoesActionState>;
  button: string;
  children: ReactNode;
}>) {
  const [state, formAction, pending] = useActionState(action, initialState);
  return (
    <form action={formAction} className="grid gap-3 rounded-md border bg-muted/20 p-3">
      {children}
      <Button disabled={pending} type="submit">{pending ? "Enviando..." : button}</Button>
      <ActionFeedback state={state} />
    </form>
  );
}

export function ConfiguracoesActions({
  activateAction,
  approveAction,
  captureSnapshotAction,
  createCalendarioAction,
  createConfiguracaoAction,
  createModalidadeAction,
  inactivateAction,
  programAction,
}: ConfiguracoesActionsProps) {
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <ActionForm action={createModalidadeAction} button="Criar modalidade">
        <h3 className="font-semibold">Modalidade</h3>
        <Label htmlFor="modalidade_codigo">Codigo</Label>
        <Input id="modalidade_codigo" name="modalidade_codigo" required />
        <Label htmlFor="modalidade_nome">Nome</Label>
        <Input id="modalidade_nome" name="modalidade_nome" required />
      </ActionForm>

      <ActionForm action={createCalendarioAction} button="Criar calendario">
        <h3 className="font-semibold">Calendario</h3>
        <Label htmlFor="calendario_codigo">Codigo</Label>
        <Input id="calendario_codigo" name="calendario_codigo" required />
        <Label htmlFor="calendario_nome">Nome</Label>
        <Input id="calendario_nome" name="calendario_nome" required />
        <Label htmlFor="feriados">Feriados separados por virgula</Label>
        <Input id="feriados" name="feriados" placeholder="2026-01-01,2026-12-25" />
      </ActionForm>

      <ActionForm action={createConfiguracaoAction} button="Criar configuracao">
        <h3 className="font-semibold">Configuracao financeira</h3>
        <Label htmlFor="config_modalidade">Modalidade</Label>
        <Input id="config_modalidade" name="config_modalidade" required />
        <Label htmlFor="config_calendario_id">ID do calendario</Label>
        <Input id="config_calendario_id" name="config_calendario_id" required />
        <Label htmlFor="vigencia_inicio">Vigencia inicio</Label>
        <Input id="vigencia_inicio" name="vigencia_inicio" required type="date" />
        <Label htmlFor="vigencia_fim">Vigencia fim</Label>
        <Input id="vigencia_fim" name="vigencia_fim" type="date" />
        <Label htmlFor="taxas_json">Taxas</Label>
        <Input id="taxas_json" name="taxas_json" required defaultValue='[{"nome":"taxa_base","valor":"0.00","periodicidade":"mensal"}]' />
        <Label htmlFor="parametros_json">Parametros</Label>
        <Input id="parametros_json" name="parametros_json" required defaultValue='[{"nome":"limite","valor":"definido_pela_operacao"}]' />
        <Label htmlFor="politica_json">Politica de arredondamento</Label>
        <Input id="politica_json" name="politica_json" required defaultValue='{"modo":"meio_para_cima","escala":2}' />
      </ActionForm>

      <ActionForm action={approveAction} button="Aprovar">
        <h3 className="font-semibold">Decisao</h3>
        <Label htmlFor="aprovar_configuracao_id">ID da configuracao</Label>
        <Input id="aprovar_configuracao_id" name="configuracao_id" required />
        <Label htmlFor="aprovar_motivo">Motivo opcional</Label>
        <Input id="aprovar_motivo" name="motivo" />
      </ActionForm>

      <ActionForm action={programAction} button="Programar">
        <h3 className="font-semibold">Programacao</h3>
        <Label htmlFor="programar_configuracao_id">ID da configuracao</Label>
        <Input id="programar_configuracao_id" name="configuracao_id" required />
        <Label htmlFor="data_ativacao">Data de ativacao</Label>
        <Input id="data_ativacao" name="data_ativacao" required type="date" />
        <Label htmlFor="programar_motivo">Motivo opcional</Label>
        <Input id="programar_motivo" name="motivo" />
      </ActionForm>

      <ActionForm action={activateAction} button="Ativar">
        <h3 className="font-semibold">Ativacao</h3>
        <Label htmlFor="ativar_configuracao_id">ID da configuracao</Label>
        <Input id="ativar_configuracao_id" name="configuracao_id" required />
      </ActionForm>

      <ActionForm action={inactivateAction} button="Inativar">
        <h3 className="font-semibold">Inativacao</h3>
        <Label htmlFor="inativar_configuracao_id">ID da configuracao</Label>
        <Input id="inativar_configuracao_id" name="configuracao_id" required />
      </ActionForm>

      <ActionForm action={captureSnapshotAction} button="Capturar snapshot">
        <h3 className="font-semibold">Snapshot contratual</h3>
        <Label htmlFor="snapshot_configuracao_id">ID da configuracao</Label>
        <Input id="snapshot_configuracao_id" name="configuracao_id" required />
        <Label htmlFor="snapshot_motivo">Motivo opcional</Label>
        <Input id="snapshot_motivo" name="motivo" />
      </ActionForm>
    </div>
  );
}
