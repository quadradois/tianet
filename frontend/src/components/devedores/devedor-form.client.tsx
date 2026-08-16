"use client";

import { useActionState } from "react";

import type { Devedor, DevedorActionState } from "../../lib/devedores/devedores-policy";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Label } from "../ui/label";

type DevedorFormProps = Readonly<{
  action: (state: DevedorActionState, formData: FormData) => Promise<DevedorActionState>;
  initialState: DevedorActionState;
  devedor?: Devedor;
  mode: "create" | "update";
}>;

export function DevedorForm({ action, devedor, initialState, mode }: DevedorFormProps) {
  const [state, formAction, pending] = useActionState(action, initialState);
  const contato = devedor?.contatos[0];
  return (
    <form action={formAction} className="grid gap-4 rounded-lg border bg-card p-4" data-state={state.kind}>
      <div>
        <h2 className="text-lg font-semibold">{mode === "create" ? "Cadastrar Devedor" : "Atualizar dados cadastrais"}</h2>
        <p className="text-sm text-muted-foreground">
          Dados enviados ao backend oficial. Tenant e Carteira nao fazem parte do formulario.
        </p>
      </div>
      {mode === "update" && devedor ? <input name="devedor_id" type="hidden" value={devedor.id} /> : null}
      <div className="grid gap-2">
        <Label htmlFor={`${mode}-documento`}>Documento</Label>
        <Input
          autoComplete="off"
          defaultValue={devedor?.documento ?? ""}
          disabled={mode === "update"}
          id={`${mode}-documento`}
          maxLength={20}
          minLength={1}
          name="documento"
          required={mode === "create"}
        />
        {mode === "update" ? <p className="text-xs text-muted-foreground">Documento e imutavel na API.</p> : null}
      </div>
      <div className="grid gap-2">
        <Label htmlFor={`${mode}-nome`}>Nome</Label>
        <Input autoComplete="name" defaultValue={devedor?.nome ?? ""} id={`${mode}-nome`} maxLength={200} minLength={1} name="nome" required />
      </div>
      <fieldset className="grid gap-3 rounded-md border p-3">
        <legend className="px-1 text-sm font-semibold">Contato principal</legend>
        <div className="grid gap-2 sm:grid-cols-[10rem_1fr]">
          <div className="grid gap-2">
            <Label htmlFor={`${mode}-contato-tipo`}>Tipo</Label>
            <select className="min-h-(--size-control) rounded-md border bg-background px-3 text-sm" defaultValue={contato?.tipo ?? "email"} id={`${mode}-contato-tipo`} name="contato_tipo">
              <option value="email">E-mail</option>
              <option value="telefone">Telefone</option>
              <option value="whatsapp">WhatsApp</option>
            </select>
          </div>
          <div className="grid gap-2">
            <Label htmlFor={`${mode}-contato-valor`}>Valor</Label>
            <Input autoComplete="off" defaultValue={contato?.valor ?? ""} id={`${mode}-contato-valor`} maxLength={254} minLength={1} name="contato_valor" required />
          </div>
        </div>
        <label className="flex min-h-(--size-control) items-center gap-2 text-sm">
          <input defaultChecked={contato?.preferencial ?? true} name="contato_preferencial" type="checkbox" />
          Contato preferencial
        </label>
      </fieldset>
      <Button disabled={pending} type="submit">{pending ? "Enviando..." : mode === "create" ? "Cadastrar" : "Salvar alteracoes"}</Button>
      <p aria-live="polite" className="text-sm" role={state.kind === "problem" ? "alert" : "status"}>
        {state.message}
        {state.correlationId ? <> Correlation ID: {state.correlationId}</> : null}
      </p>
    </form>
  );
}
