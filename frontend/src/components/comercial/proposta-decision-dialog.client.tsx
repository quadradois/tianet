"use client";

import { useActionState } from "react";

import type { ComercialActionState, Proposal } from "../../lib/comercial/comercial-policy";
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

type DecisionAction = (state: ComercialActionState, formData: FormData) => Promise<ComercialActionState>;

type DecisionDialogProps = Readonly<{
  action: DecisionAction;
  decision: "enviar-para-analise" | "aprovar" | "recusar" | "cancelar" | "expirar";
  initialState: ComercialActionState;
  proposal: Proposal;
}>;

const LABELS = {
  "enviar-para-analise": "Enviar para analise",
  aprovar: "Aprovar proposta",
  recusar: "Recusar proposta",
  cancelar: "Cancelar proposta",
  expirar: "Expirar proposta",
} as const;

export function PropostaDecisionDialog({ action, decision, initialState, proposal }: DecisionDialogProps) {
  const [state, formAction, pending] = useActionState(action, initialState);
  const requiresReason = decision === "recusar" || decision === "cancelar";
  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant={decision === "aprovar" || decision === "enviar-para-analise" ? "default" : "outline"}>
          {LABELS[decision]}
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{LABELS[decision]}</DialogTitle>
          <DialogDescription>
            A decisao sera enviada ao backend para a proposta {proposal.id}. O frontend nao altera estado localmente.
          </DialogDescription>
        </DialogHeader>
        <form action={formAction} className="grid gap-4">
          <input name="proposta_id" type="hidden" value={proposal.id} />
          <input name="decision" type="hidden" value={decision} />
          {requiresReason ? (
            <div className="grid gap-2">
              <Label htmlFor={`${decision}-motivo`}>Motivo opcional</Label>
              <textarea className="min-h-24 rounded-md border bg-background p-3 text-sm" id={`${decision}-motivo`} maxLength={500} name="motivo" />
            </div>
          ) : null}
          <p aria-live="polite" className="text-sm text-muted-foreground">
            {state.message}{state.correlationId ? ` Correlation ID: ${state.correlationId}` : ""}
          </p>
          <DialogFooter>
            <DialogClose asChild><Button type="button" variant="outline">Fechar</Button></DialogClose>
            <Button disabled={pending} type="submit">{pending ? "Enviando..." : LABELS[decision]}</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
