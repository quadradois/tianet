"use client";

import { useActionState, useState } from "react";

import type { NumeroAvisosActionState } from "../../lib/whatsapp/whatsapp-policy";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Label } from "../ui/label";

type Action = (state: NumeroAvisosActionState, formData: FormData) => Promise<NumeroAvisosActionState>;

type NumeroAvisosCardProps = Readonly<{
  action: Action;
  initialState: NumeroAvisosActionState;
  numero: string | null;
  podeGerir: boolean;
}>;

/**
 * Numero que recebe os avisos do sistema (resumo diario de acertos, sobra de
 * pagamento). NAO e o telefone pareado acima: e o destino das mensagens.
 *
 * A `Idempotency-Key` nasce no cliente e e trocada a cada ENVIO: o retry de
 * rede do mesmo envio e replay; "corrigi e salvei de novo" e uma segunda
 * escrita legitima, com chave propria. O botao desabilitado durante o envio
 * cobre o duplo clique.
 */
export function NumeroAvisosCard({ action, initialState, numero, podeGerir }: NumeroAvisosCardProps) {
  const [state, formAction, pendente] = useActionState(action, initialState);
  const [chave, setChave] = useState(() => crypto.randomUUID());
  const enviar = (dados: FormData) => {
    formAction(dados);
    setChave(crypto.randomUUID());
  };

  const atual = state.kind === "success" ? state.numero : numero;

  return (
    <div className="grid gap-4 rounded-xl border border-border bg-card p-5">
      <div className="grid gap-1">
        <h2 className="font-semibold">Avisos do sistema</h2>
        <p className="text-sm text-muted-foreground">
          O resumo diario de acertos e o aviso de sobra de pagamento sao enviados para este numero.
        </p>
        {atual ? (
          <p className="text-sm">Recebe os avisos: <span className="font-medium">{atual}</span></p>
        ) : (
          <p className="text-sm text-destructive">Nenhum numero cadastrado — os avisos nao saem ate cadastrar um.</p>
        )}
      </div>

      {state.kind !== "idle" ? (
        <p
          className={state.kind === "problem" ? "rounded-md border border-destructive/40 bg-destructive/5 p-3 text-sm" : "rounded-md border border-border bg-muted/40 p-3 text-sm"}
          role={state.kind === "problem" ? "alert" : "status"}
        >
          {state.message}
          {state.kind === "problem" ? <span className="mt-1 block text-xs text-muted-foreground">Correlation ID: {state.correlationId}</span> : null}
        </p>
      ) : null}

      {podeGerir ? (
        <form action={enviar} className="grid max-w-sm gap-2">
          <input name="idempotency_key" type="hidden" value={chave} />
          <Label htmlFor="numero-avisos">Numero que recebe os avisos</Label>
          <Input
            autoComplete="tel"
            defaultValue={atual ?? ""}
            id="numero-avisos"
            inputMode="tel"
            name="numero"
            placeholder="5511999998888"
            required
          />
          <p className="text-xs text-muted-foreground">Com DDI e DDD, so numeros. Ex.: 5511999998888.</p>
          <Button className="justify-self-start" disabled={pendente} type="submit">
            {pendente ? "Salvando..." : "Salvar numero"}
          </Button>
        </form>
      ) : null}
    </div>
  );
}
