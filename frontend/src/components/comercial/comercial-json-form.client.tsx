"use client";

import { useActionState } from "react";

import type { ComercialActionState } from "../../lib/comercial/comercial-policy";
import { Button } from "../ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/card";
import { Input } from "../ui/input";
import { Label } from "../ui/label";

type Action = (state: ComercialActionState, formData: FormData) => Promise<ComercialActionState>;

type JsonFormProps = Readonly<{
  action: Action;
  devedorId?: string;
  initialState: ComercialActionState;
  mode: "simulation" | "proposal" | "proposal-update";
  propostaId?: string;
}>;

const DEFAULT_PARAMETERS = '{\n  "produto": "credito-pessoal",\n  "canal": "operacao-assistida"\n}';

export function ComercialJsonForm({ action, devedorId, initialState, mode, propostaId }: JsonFormProps) {
  const [state, formAction, pending] = useActionState(action, initialState);
  const title = mode === "simulation"
    ? "Criar simulacao comercial"
    : mode === "proposal"
      ? "Criar proposta comercial"
      : "Atualizar proposta comercial";
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>Informe as condicoes comerciais. O sistema valida e calcula as regras finais.</CardDescription>
      </CardHeader>
      <CardContent>
        <form action={formAction} className="grid gap-4">
          {devedorId ? <input name="devedor_id" type="hidden" value={devedorId} /> : null}
          {propostaId ? <input name="proposta_id" type="hidden" value={propostaId} /> : null}
          {mode === "proposal" ? (
            <div className="grid gap-2">
              <Label htmlFor="simulacao_id">Simulacao vinculada opcional</Label>
              <Input id="simulacao_id" maxLength={36} name="simulacao_id" placeholder="ID da simulacao, se houver" />
            </div>
          ) : null}
          <div className="grid gap-2">
            <Label htmlFor={`${mode}-parametros`}>Condicoes comerciais</Label>
            <textarea
              className="min-h-40 rounded-md border bg-background p-3 font-mono text-sm"
              defaultValue={DEFAULT_PARAMETERS}
              id={`${mode}-parametros`}
              maxLength={5_000}
              name="parametros"
            />
          </div>
          <Button disabled={pending} type="submit">{pending ? "Enviando..." : title}</Button>
          <p aria-live="polite" className="text-sm text-muted-foreground">
            {state.message}{state.correlationId ? ` Correlation ID: ${state.correlationId}` : ""}
          </p>
        </form>
      </CardContent>
    </Card>
  );
}
