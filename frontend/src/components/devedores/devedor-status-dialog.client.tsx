"use client";

import { useActionState, useId } from "react";

import type { Devedor, DevedorActionState } from "../../lib/devedores/devedores-policy";
import { Button } from "../ui/button";

type StatusDialogProps = Readonly<{
  action: (state: DevedorActionState, formData: FormData) => Promise<DevedorActionState>;
  devedor: Devedor;
  initialState: DevedorActionState;
  operation: "inativar" | "reativar";
}>;

export function DevedorStatusDialog({ action, devedor, initialState, operation }: StatusDialogProps) {
  const [state, formAction, pending] = useActionState(action, initialState);
  const descriptionId = useId();
  const destructive = operation === "inativar";
  return (
    <form action={formAction} aria-describedby={descriptionId} className="grid gap-2 rounded-lg border bg-card p-4">
      <input name="devedor_id" type="hidden" value={devedor.id} />
      <p className="font-semibold">{destructive ? "Inativar Devedor" : "Reativar Devedor"}</p>
      <p className="text-sm text-muted-foreground" id={descriptionId}>
        A transicao e autorizada e validada pelo backend. O frontend apenas envia o comando idempotente.
      </p>
      <Button disabled={pending} type="submit" variant={destructive ? "destructive" : "success"}>
        {pending ? "Processando..." : destructive ? "Inativar" : "Reativar"}
      </Button>
      <p aria-live="polite" className="text-sm" role={state.kind === "problem" ? "alert" : "status"}>
        {state.message}
        {state.correlationId ? <> Correlation ID: {state.correlationId}</> : null}
      </p>
    </form>
  );
}
