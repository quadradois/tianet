"use client";

import { useActionState, useId } from "react";

import { Button } from "../ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "../ui/dialog";
import { Label } from "../ui/label";

import type { Contract, ContractDecision, ContratoActionState } from "../../lib/contratos/contratos-policy";

type Action = (state: ContratoActionState, formData: FormData) => Promise<ContratoActionState>;

const LABELS: Record<ContractDecision, string> = {
  assinar: "Assinar contrato",
  "liberar-para-motor": "Liberar contrato para Motor",
  cancelar: "Cancelar contrato",
  encerrar: "Encerrar contrato",
};

const DESCRIPTIONS: Record<ContractDecision, string> = {
  assinar: "Registra a assinatura ou formalizacao permitida pelo backend.",
  "liberar-para-motor": "Gera somente a saida logica para o Motor futuro. Nao cria Emprestimo, Parcela ou Pagamento.",
  cancelar: "Cancela contrato ainda nao liberado quando o estado backend permitir.",
  encerrar: "Encerra administrativamente sem substituir quitacao, liquidacao ou renegociacao financeira.",
};

export function ContratoDecisionDialog({ action, contract, decision, initialState }: Readonly<{
  action: Action;
  contract: Contract;
  decision: ContractDecision;
  initialState: ContratoActionState;
}>) {
  const [state, formAction, pending] = useActionState(action, initialState);
  const reasonId = useId();
  const needsReason = decision === "cancelar" || decision === "encerrar";
  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant={decision === "cancelar" || decision === "encerrar" ? "destructive" : "default"}>{LABELS[decision]}</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{LABELS[decision]}</DialogTitle>
          <DialogDescription>{DESCRIPTIONS[decision]}</DialogDescription>
        </DialogHeader>
        <form action={formAction} className="grid gap-4">
          <input name="contrato_id" type="hidden" value={contract.id} />
          <input name="decision" type="hidden" value={decision} />
          {needsReason ? (
            <div className="grid gap-2">
              <Label htmlFor={reasonId}>Motivo opcional</Label>
              <textarea
                className="min-h-28 rounded-md border bg-background p-3 text-sm"
                id={reasonId}
                maxLength={500}
                name="motivo"
                placeholder="Motivo contratual, sem dados financeiros novos"
              />
            </div>
          ) : null}
          {state.kind !== "idle" ? (
            <p aria-live="polite" className={state.kind === "problem" ? "text-sm text-destructive" : "text-sm text-success"}>
              {state.message}{state.correlationId ? ` Correlation ID: ${state.correlationId}` : ""}
            </p>
          ) : null}
          <DialogFooter>
            <DialogClose asChild><Button type="button" variant="outline">Fechar</Button></DialogClose>
            <Button disabled={pending} type="submit">{pending ? "Enviando..." : LABELS[decision]}</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export function ContratoCreateForm({ action, initialProposalId, initialState }: Readonly<{
  action: Action;
  initialProposalId?: string | undefined;
  initialState: ContratoActionState;
}>) {
  const [state, formAction, pending] = useActionState(action, initialState);
  return (
    <form action={formAction} className="grid gap-3 rounded-lg border bg-card p-4">
      <div className="grid gap-2">
        <Label htmlFor="proposta_comercial_id">Proposta aprovada</Label>
        <input
          className="min-h-(--size-control) rounded-md border bg-background px-3 text-sm"
          defaultValue={initialProposalId ?? ""}
          id="proposta_comercial_id"
          maxLength={36}
          name="proposta_comercial_id"
          placeholder="UUID da proposta aprovada"
        />
      </div>
      <p className="text-xs text-muted-foreground">A formalizacao copia parametros aprovados do backend; o frontend nao calcula valores financeiros.</p>
      {state.kind !== "idle" ? (
        <p aria-live="polite" className={state.kind === "problem" ? "text-sm text-destructive" : "text-sm text-success"}>
          {state.message}{state.correlationId ? ` Correlation ID: ${state.correlationId}` : ""}
        </p>
      ) : null}
      <Button disabled={pending} type="submit">{pending ? "Formalizando..." : "Formalizar contrato"}</Button>
    </form>
  );
}
