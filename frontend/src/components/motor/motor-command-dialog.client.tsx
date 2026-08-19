"use client";

import { useActionState } from "react";

import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import type { MotorActionState, MotorCommand } from "../../lib/motor/motor-policy";

type Action = (state: MotorActionState, formData: FormData) => Promise<MotorActionState>;

function Status({ state }: Readonly<{ state: MotorActionState }>) {
  if (state.kind === "idle") return null;
  return (
    <p aria-live="polite" className={state.kind === "success" ? "text-sm text-success" : "text-sm text-danger"}>
      {state.message}{state.correlationId ? ` Correlation ID: ${state.correlationId}` : ""}
    </p>
  );
}

export function CreateLoanForm({ action, initialContractId, initialState }: Readonly<{
  action: Action;
  initialContractId?: string | undefined;
  initialState: MotorActionState;
}>) {
  const [state, formAction, pending] = useActionState(action, initialState);
  return (
    <form action={formAction} className="grid gap-3 rounded-lg border bg-card p-4 md:grid-cols-[1fr_14rem_auto]">
      <div className="grid gap-2">
        <Label htmlFor="contrato_id">Contrato liberado</Label>
        <Input defaultValue={initialContractId ?? ""} id="contrato_id" name="contrato_id" placeholder="UUID do Contrato liberado" />
      </div>
      <div className="grid gap-2">
        <Label htmlFor="idempotency_key">Idempotency-Key</Label>
        <Input id="idempotency_key" name="idempotency_key" placeholder="opcional; gerada se vazia" />
      </div>
      <Button className="self-end" disabled={pending} type="submit">Criar Emprestimo</Button>
      <div className="md:col-span-3"><Status state={state} /></div>
    </form>
  );
}

export function MotorCommandForm({ action, command, emprestimoId, hoje, initialState }: Readonly<{
  action: Action;
  command: MotorCommand;
  emprestimoId: string;
  /** Hoje, vindo do servidor: o navegador nao escolhe data de operacao financeira. */
  hoje: string;
  initialState: MotorActionState;
}>) {
  const [state, formAction, pending] = useActionState(action, initialState);
  const title = command === "gerar-parcelas"
    ? "Gerar parcelas"
    : command === "registrar-pagamento"
      ? "Registrar pagamento"
      : command === "executar-quitacao"
        ? "Executar quitacao"
        : "Registrar renegociacao";
  const evidence = command === "gerar-parcelas"
    ? "sem-idempotency:/credit/emprestimos/{emprestimo_id}/parcelas"
    : command === "registrar-pagamento"
      ? "Pagamento idempotente registrado pelo Motor."
      : command === "executar-quitacao"
        ? "Quitacao oficial executada pelo Motor."
        : "Renegociacao opaca registrada sem formula local.";
  return (
    <form action={formAction} className="grid gap-3 rounded-lg border bg-card p-4">
      <h3 className="font-semibold">{title}</h3>
      <p className="text-sm text-muted-foreground">Os valores sao calculados pelo sistema.</p>
      <p className="sr-only">{evidence}</p>
      <input name="command" type="hidden" value={command} />
      <input name="emprestimo_id" type="hidden" value={emprestimoId} />
      {command === "gerar-parcelas" ? (
        <div className="grid gap-2">
          <Label htmlFor={`${command}-data_referencia`}>Data de referencia</Label>
          <Input defaultValue="2026-08-14" id={`${command}-data_referencia`} name="data_referencia" type="date" />
        </div>
      ) : null}
      {command === "registrar-pagamento" ? (
        <>
          <div className="grid gap-2">
            <Label htmlFor={`${command}-valor`}>Quanto o devedor pagou</Label>
            <Input id={`${command}-valor`} inputMode="decimal" name="valor" placeholder="100.00" />
          </div>
          <div className="grid gap-2">
            <Label htmlFor={`${command}-recebido_em`}>Data do pagamento</Label>
            <Input defaultValue={hoje} id={`${command}-recebido_em`} name="recebido_em" type="date" />
          </div>
        </>
      ) : null}
      {command === "executar-quitacao" ? (
        <div className="grid gap-2">
          <Label htmlFor={`${command}-recebido_em`}>Data do pagamento</Label>
          <Input defaultValue={hoje} id={`${command}-recebido_em`} name="recebido_em" type="date" />
        </div>
      ) : null}
      {command === "registrar-renegociacao" ? (
        <>
          <div className="grid gap-2">
            <Label htmlFor={`${command}-renegociado_em`}>Renegociado em</Label>
            <Input defaultValue={hoje} id={`${command}-renegociado_em`} name="renegociado_em" type="date" />
          </div>
          <div className="grid gap-2">
            <Label htmlFor={`${command}-novos_parametros`}>Novos parametros opacos</Label>
            <textarea className="min-h-24 rounded-md border bg-background p-3 text-sm" defaultValue={'{"origem":"atendimento"}'} id={`${command}-novos_parametros`} name="novos_parametros" />
          </div>
        </>
      ) : null}
      {/* Idempotency-Key nao e pedida ao Credor: e protocolo, nao decisao dele.
          A camada BFF gera uma quando o campo nao vem, e a protecao contra
          duplicidade continua exatamente igual. */}
      <Status state={state} />
      <Button disabled={pending} type="submit">{title}</Button>
    </form>
  );
}
