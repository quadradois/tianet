"use client";

import { useActionState } from "react";

import type { CobrancaActionState, CobrancaActionType, CobrancaCase } from "../../lib/cobranca/cobranca-policy";
import { mascaraMoeda } from "../../lib/formato/brasileiro";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Label } from "../ui/label";

type Action = (state: CobrancaActionState, formData: FormData) => Promise<CobrancaActionState>;

function Status({ state }: Readonly<{ state: CobrancaActionState }>) {
  if (state.kind === "idle") return null;
  return (
    <p aria-live="polite" className={state.kind === "success" ? "text-sm text-success" : "text-sm text-destructive"}>
      {state.message}{state.correlationId ? ` Correlation ID: ${state.correlationId}` : ""}
    </p>
  );
}

function IdempotencyField({ id }: Readonly<{ id: string }>) {
  return <input id={id} name="idempotency_key" type="hidden" />;
}

export function CobrancaActionForm({ action, caseItem, initialState }: Readonly<{
  action: Action;
  caseItem: CobrancaCase;
  initialState: CobrancaActionState;
}>) {
  const [state, formAction, pending] = useActionState(action, initialState);
  const actionTypes: readonly CobrancaActionType[] = ["contato", "telefone", "email", "visita", "outro"];
  return (
    <form action={formAction} className="grid gap-3 rounded-lg border bg-card p-4">
      <h3 className="font-semibold">Registrar acao manual</h3>
      <p className="text-xs text-muted-foreground">Registre o contato feito e o resultado combinado.</p>
      <input name="caso_id" type="hidden" value={caseItem.caso_id} />
      <div className="grid gap-2">
        <Label htmlFor={`${caseItem.caso_id}-tipo`}>Tipo</Label>
        <select className="min-h-(--size-control) rounded-md border bg-background px-3 text-sm" id={`${caseItem.caso_id}-tipo`} name="tipo">
          {actionTypes.map((tipo) => <option key={tipo} value={tipo}>{tipo}</option>)}
        </select>
      </div>
      <div className="grid gap-2">
        <Label htmlFor={`${caseItem.caso_id}-resultado`}>Resultado</Label>
        <textarea className="min-h-20 rounded-md border bg-background p-3 text-sm" id={`${caseItem.caso_id}-resultado`} name="resultado" placeholder="Descreva o resultado operacional" />
      </div>
      <IdempotencyField id={`${caseItem.caso_id}-acao-idempotency`} />
      <Status state={state} />
      <Button disabled={pending} type="submit">Registrar acao</Button>
    </form>
  );
}

export function PromiseForm({ action, caseItem, initialState }: Readonly<{
  action: Action;
  caseItem: CobrancaCase;
  initialState: CobrancaActionState;
}>) {
  const [state, formAction, pending] = useActionState(action, initialState);
  return (
    <form action={formAction} className="grid gap-3 rounded-lg border bg-card p-4">
      <h3 className="font-semibold">Registrar promessa</h3>
      <p className="text-xs text-muted-foreground">Use quando o devedor prometeu pagar um valor em uma data.</p>
      <input name="caso_id" type="hidden" value={caseItem.caso_id} />
      <div className="grid gap-2">
        <Label htmlFor={`${caseItem.caso_id}-valor`}>Valor declarado</Label>
        <Input
          id={`${caseItem.caso_id}-valor`}
          inputMode="decimal"
          name="valor_declarado"
          onBlur={(event) => {
            event.currentTarget.value = mascaraMoeda(event.currentTarget.value);
          }}
          placeholder="R$ 100,00"
        />
      </div>
      <div className="grid gap-2">
        <Label htmlFor={`${caseItem.caso_id}-data-promessa`}>Data da promessa</Label>
        <Input id={`${caseItem.caso_id}-data-promessa`} name="data_promessa" type="date" />
      </div>
      <label className="flex items-center gap-2 text-sm">
        <input name="pagamento_informado" type="checkbox" />
        Pagamento informado pelo atendimento
      </label>
      <div className="grid gap-2">
        <Label htmlFor={`${caseItem.caso_id}-observacao`}>Observacao</Label>
        <textarea className="min-h-20 rounded-md border bg-background p-3 text-sm" id={`${caseItem.caso_id}-observacao`} name="observacao" placeholder="Opcional" />
      </div>
      <IdempotencyField id={`${caseItem.caso_id}-promessa-idempotency`} />
      <Status state={state} />
      <Button disabled={pending} type="submit">Registrar promessa</Button>
    </form>
  );
}

export function AppropriationForm({ action, caseItem, initialState }: Readonly<{
  action: Action;
  caseItem: CobrancaCase;
  initialState: CobrancaActionState;
}>) {
  const [state, formAction, pending] = useActionState(action, initialState);
  return (
    <form action={formAction} className="grid gap-3 rounded-lg border bg-card p-4">
      <h3 className="font-semibold">Conciliar pagamento</h3>
      <p className="text-xs text-muted-foreground">Associe um pagamento recebido a uma promessa registrada.</p>
      <div className="grid gap-2">
        <Label htmlFor={`${caseItem.caso_id}-promessa-id`}>Promessa</Label>
        <Input id={`${caseItem.caso_id}-promessa-id`} name="promessa_id" placeholder="ID da promessa" />
      </div>
      <div className="grid gap-2">
        <Label htmlFor={`${caseItem.caso_id}-pagamento-id`}>Pagamento</Label>
        <Input id={`${caseItem.caso_id}-pagamento-id`} name="pagamento_id" placeholder="ID do pagamento" />
      </div>
      <div className="grid gap-2">
        <Label htmlFor={`${caseItem.caso_id}-data-referencia`}>Data de referencia (opcional)</Label>
        <Input id={`${caseItem.caso_id}-data-referencia`} name="data_referencia" type="date" />
      </div>
      <IdempotencyField id={`${caseItem.caso_id}-apropriacao-idempotency`} />
      <Status state={state} />
      <Button disabled={pending} type="submit">Conciliar pagamento</Button>
    </form>
  );
}
