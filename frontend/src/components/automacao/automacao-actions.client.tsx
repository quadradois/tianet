"use client";

import { useActionState } from "react";

import { INITIAL_AUTOMACAO_ACTION_STATE, type AutomacaoActionState } from "../../lib/automacao/automacao-policy";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Label } from "../ui/label";

type Action = (state: AutomacaoActionState, formData: FormData) => Promise<AutomacaoActionState>;

export type AutomacaoActionsProps = Readonly<{
  activateTemplateAction: Action;
  approveTemplateAction: Action;
  cancelJobAction: Action;
  createTemplateAction: Action;
  reconcileNotificationAction: Action;
  retryJobAction: Action;
}>;

function ActionMessage({ state }: Readonly<{ state: AutomacaoActionState }>) {
  if (state.kind === "idle") return null;
  return (
    <p className={state.kind === "success" ? "text-sm text-success" : "text-sm text-destructive"} role="status">
      {state.message}{state.correlationId ? ` Correlation ID: ${state.correlationId}` : ""}
    </p>
  );
}

function useAction(action: Action) {
  return useActionState(action, INITIAL_AUTOMACAO_ACTION_STATE);
}

export function AutomacaoActions(props: AutomacaoActionsProps) {
  const [cancelState, cancelForm] = useAction(props.cancelJobAction);
  const [retryState, retryForm] = useAction(props.retryJobAction);
  const [createState, createForm] = useAction(props.createTemplateAction);
  const [approveState, approveForm] = useAction(props.approveTemplateAction);
  const [activateState, activateForm] = useAction(props.activateTemplateAction);
  const [reconcileState, reconcileForm] = useAction(props.reconcileNotificationAction);
  return (
    <section aria-labelledby="automacao-actions-title" className="grid gap-4">
      <div>
        <h2 className="text-xl font-semibold" id="automacao-actions-title">Comandos de Automacao</h2>
        <p className="text-sm text-muted-foreground">Comandos restritos aos contratos de job, template e conciliacao de notificacao.</p>
      </div>
      <div className="grid min-w-0 gap-4 xl:grid-cols-2">
        <form action={cancelForm} className="grid min-w-0 gap-3 rounded-lg border bg-card p-4">
          <Label htmlFor="automacao-cancel-job">job_id</Label>
          <Input id="automacao-cancel-job" name="job_id" required />
          <Button type="submit" variant="outline">Cancelar job</Button>
          <ActionMessage state={cancelState} />
        </form>
        <form action={retryForm} className="grid min-w-0 gap-3 rounded-lg border bg-card p-4">
          <Label htmlFor="automacao-retry-job">job_id</Label>
          <Input id="automacao-retry-job" name="job_id" required />
          <Button type="submit">Retry job</Button>
          <ActionMessage state={retryState} />
        </form>
        <form action={createForm} className="grid min-w-0 gap-3 rounded-lg border bg-card p-4">
          <Label htmlFor="automacao-template-codigo">Codigo do template</Label>
          <Input id="automacao-template-codigo" maxLength={120} name="codigo" required />
          <Label htmlFor="automacao-template-versao">Versao</Label>
          <Input id="automacao-template-versao" min={1} name="versao" required type="number" />
          <Label htmlFor="automacao-template-assunto">Assunto</Label>
          <Input id="automacao-template-assunto" maxLength={300} name="assunto" required />
          <Label htmlFor="automacao-template-corpo">Corpo</Label>
          <textarea className="min-h-24 rounded-md border bg-background px-3 py-2 text-sm" id="automacao-template-corpo" maxLength={5000} name="corpo" required />
          <Button type="submit">Criar template</Button>
          <ActionMessage state={createState} />
        </form>
        <form action={approveForm} className="grid min-w-0 gap-3 rounded-lg border bg-card p-4">
          <Label htmlFor="automacao-approve-template">template_id</Label>
          <Input id="automacao-approve-template" name="template_id" required />
          <Button type="submit">Aprovar template</Button>
          <ActionMessage state={approveState} />
        </form>
        <form action={activateForm} className="grid min-w-0 gap-3 rounded-lg border bg-card p-4">
          <Label htmlFor="automacao-activate-template">template_id</Label>
          <Input id="automacao-activate-template" name="template_id" required />
          <Button type="submit">Ativar template</Button>
          <ActionMessage state={activateState} />
        </form>
        <form action={reconcileForm} className="grid min-w-0 gap-3 rounded-lg border bg-card p-4">
          <Label htmlFor="automacao-reconcile-notification">notification_id</Label>
          <Input id="automacao-reconcile-notification" name="notification_id" required />
          <Label htmlFor="automacao-reconcile-provider">provider_message_id</Label>
          <Input id="automacao-reconcile-provider" name="provider_message_id" required />
          <Label htmlFor="automacao-reconcile-motivo">Motivo</Label>
          <Input id="automacao-reconcile-motivo" maxLength={500} name="motivo" required />
          <Label htmlFor="automacao-reconcile-idem">Idempotency-Key</Label>
          <Input id="automacao-reconcile-idem" maxLength={255} name="idempotency_key" required />
          <Button type="submit">Conciliar notificacao</Button>
          <ActionMessage state={reconcileState} />
        </form>
      </div>
    </section>
  );
}
