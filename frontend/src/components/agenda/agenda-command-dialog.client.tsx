"use client";

import { useActionState } from "react";

import type { AgendaActionState, AgendaItem, Reminder } from "../../lib/agenda/agenda-policy";
import { Button } from "../ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/card";
import { Input } from "../ui/input";
import { Label } from "../ui/label";

type Action = (state: AgendaActionState, formData: FormData) => Promise<AgendaActionState>;

function StatusMessage({ state }: Readonly<{ state: AgendaActionState }>) {
  if (state.kind === "idle") return <p className="text-xs text-muted-foreground">{state.message}</p>;
  return (
    <p className={state.kind === "success" ? "text-xs text-success" : "text-xs text-destructive"} role={state.kind === "problem" ? "alert" : "status"}>
      {state.message}{state.correlationId ? ` Correlation ID: ${state.correlationId}` : ""}
    </p>
  );
}

export function CommitmentForm({ action, initialState }: Readonly<{ action: Action; initialState: AgendaActionState }>) {
  const [state, formAction, pending] = useActionState(action, initialState);
  return (
    <Card>
      <CardHeader>
        <CardTitle>Novo compromisso</CardTitle>
        <CardDescription>Compromisso idempotente criado para Devedor da Carteira atual.</CardDescription>
      </CardHeader>
      <CardContent>
        <form action={formAction} className="grid gap-3">
          <input name="command" type="hidden" value="criar-compromisso" />
          <input name="idempotency_key" type="hidden" value={crypto.randomUUID()} />
          <Label htmlFor="agenda-devedor">Devedor</Label>
          <Input id="agenda-devedor" name="devedor_id" placeholder="UUID do Devedor" required />
          <Label htmlFor="agenda-titulo">Titulo</Label>
          <Input id="agenda-titulo" name="titulo" maxLength={140} required />
          <Label htmlFor="agenda-previsto">Previsto para</Label>
          <Input id="agenda-previsto" name="previsto_para" placeholder="2026-08-14T15:00:00-03:00" required />
          <Label htmlFor="agenda-emprestimo">Emprestimo opcional</Label>
          <Input id="agenda-emprestimo" name="emprestimo_id" placeholder="UUID opcional" />
          <Button disabled={pending} type="submit">{pending ? "Registrando..." : "Criar compromisso"}</Button>
          <StatusMessage state={state} />
        </form>
      </CardContent>
    </Card>
  );
}

export function ReminderForm({ action, commitment, initialState }: Readonly<{ action: Action; commitment?: AgendaItem; initialState: AgendaActionState }>) {
  const [state, formAction, pending] = useActionState(action, initialState);
  return (
    <Card>
      <CardHeader>
        <CardTitle>Novo lembrete</CardTitle>
        <CardDescription>Lembrete idempotente vinculado ao compromisso selecionado.</CardDescription>
      </CardHeader>
      <CardContent>
        <form action={formAction} className="grid gap-3">
          <input name="command" type="hidden" value="criar-lembrete" />
          <input name="idempotency_key" type="hidden" value={crypto.randomUUID()} />
          <Label htmlFor="lembrete-compromisso">Compromisso</Label>
          <Input defaultValue={commitment?.agenda_item_id ?? ""} id="lembrete-compromisso" name="agenda_item_id" placeholder="UUID do compromisso" required />
          <Label htmlFor="lembrete-horario">Horario</Label>
          <Input id="lembrete-horario" name="horario" placeholder="2026-08-14T16:00:00-03:00" required />
          <Label htmlFor="lembrete-mensagem">Mensagem</Label>
          <Input id="lembrete-mensagem" name="mensagem" maxLength={500} required />
          <Button disabled={pending} type="submit">{pending ? "Registrando..." : "Criar lembrete"}</Button>
          <StatusMessage state={state} />
        </form>
      </CardContent>
    </Card>
  );
}

export function CommunicationForm({ action, initialState }: Readonly<{ action: Action; initialState: AgendaActionState }>) {
  const [state, formAction, pending] = useActionState(action, initialState);
  return (
    <Card>
      <CardHeader>
        <CardTitle>Registrar comunicacao</CardTitle>
        <CardDescription>Comunicacao idempotente no historico oficial, sem contato cross-carteira.</CardDescription>
      </CardHeader>
      <CardContent>
        <form action={formAction} className="grid gap-3">
          <input name="command" type="hidden" value="registrar-comunicacao" />
          <input name="idempotency_key" type="hidden" value={crypto.randomUUID()} />
          <Label htmlFor="com-devedor">Devedor</Label>
          <Input id="com-devedor" name="devedor_id" placeholder="UUID do Devedor" required />
          <Label htmlFor="com-canal">Canal</Label>
          <select className="min-h-(--size-control) rounded-md border bg-background px-3 text-sm" id="com-canal" name="canal" required>
            <option value="telefone">telefone</option>
            <option value="email">email</option>
            <option value="chat">chat</option>
            <option value="presencial">presencial</option>
          </select>
          <Label htmlFor="com-ocorrido">Ocorrido em</Label>
          <Input id="com-ocorrido" name="ocorrido_em" placeholder="2026-08-14T16:30:00-03:00" required />
          <Label htmlFor="com-resumo">Resumo</Label>
          <Input id="com-resumo" name="resumo" maxLength={1000} required />
          <Label htmlFor="com-resultado">Resultado</Label>
          <Input id="com-resultado" name="resultado" maxLength={1000} required />
          <Button disabled={pending} type="submit">{pending ? "Registrando..." : "Registrar comunicacao"}</Button>
          <StatusMessage state={state} />
        </form>
      </CardContent>
    </Card>
  );
}

export function AgendaItemCommandForm({ action, commitment, initialState }: Readonly<{ action: Action; commitment: AgendaItem; initialState: AgendaActionState }>) {
  const [state, formAction, pending] = useActionState(action, initialState);
  return (
    <form action={formAction} className="flex flex-wrap items-end gap-2">
      <input name="agenda_item_id" type="hidden" value={commitment.agenda_item_id} />
      <input name="idempotency_key" type="hidden" value={crypto.randomUUID()} />
      <input aria-label="Novo horario do compromisso" className="min-h-(--size-control) rounded-md border bg-background px-3 text-sm" name="novo_horario" placeholder="2026-08-15T10:00:00-03:00" />
      <Button disabled={pending} name="command" type="submit" value="reagendar-compromisso">Reagendar</Button>
      <Button disabled={pending} name="command" type="submit" value="concluir-compromisso">Concluir</Button>
      <Button disabled={pending} name="command" type="submit" value="cancelar-compromisso" variant="destructive">Cancelar</Button>
      <StatusMessage state={state} />
    </form>
  );
}

export function ReminderCommandForm({ action, initialState, reminder }: Readonly<{ action: Action; initialState: AgendaActionState; reminder: Reminder }>) {
  const [state, formAction, pending] = useActionState(action, initialState);
  return (
    <form action={formAction} className="grid gap-2 rounded-md border p-3">
      <input name="lembrete_id" type="hidden" value={reminder.lembrete_id} />
      <input name="idempotency_key" type="hidden" value={crypto.randomUUID()} />
      <input aria-label="Novo horario do lembrete" className="min-h-(--size-control) rounded-md border bg-background px-3 text-sm" name="novo_horario" placeholder="2026-08-15T09:00:00-03:00" />
      <input aria-label="Motivo da conciliacao" className="min-h-(--size-control) rounded-md border bg-background px-3 text-sm" name="motivo" placeholder="Motivo legado" />
      <input aria-label="Provider message id" className="min-h-(--size-control) rounded-md border bg-background px-3 text-sm" name="provider_message_id" placeholder="provider-123" />
      <input aria-label="Notification id" className="min-h-(--size-control) rounded-md border bg-background px-3 text-sm" name="notification_id" placeholder="UUID da notificacao" />
      <div className="flex flex-wrap gap-2">
        <Button disabled={pending} name="command" type="submit" value="reagendar-lembrete">Reagendar lembrete</Button>
        <Button disabled={pending} name="command" type="submit" value="enviar-lembrete">Conciliar envio</Button>
        <Button disabled={pending} name="command" type="submit" value="concluir-lembrete">Concluir lembrete</Button>
        <Button disabled={pending} name="command" type="submit" value="cancelar-lembrete" variant="destructive">Cancelar lembrete</Button>
      </div>
      <StatusMessage state={state} />
    </form>
  );
}
