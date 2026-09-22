"use client";

import { useActionState, useState } from "react";

import {
  TIPOS_CHAVE_PIX,
  type ChavePix,
  type ChavePixActionState,
} from "../../lib/pagamentos/mercadopago-policy";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Label } from "../ui/label";

type Action = (state: ChavePixActionState, formData: FormData) => Promise<ChavePixActionState>;

type Props = Readonly<{
  action: Action;
  initialState: ChavePixActionState;
  chave: ChavePix;
  podeConfigurar: boolean;
}>;

const ROTULO: Record<string, string> = {
  cpf: "CPF",
  cnpj: "CNPJ",
  telefone: "Telefone",
  email: "E-mail",
  aleatoria: "Chave aleatoria",
};

/**
 * Chave Pix da Credora — o caminho **sem taxa**.
 *
 * E o que o agente envia ao devedor: "paga aqui e me manda o comprovante".
 * Sem chave configurada o agente nao promete Pix; ele informa os valores e
 * encaminha a conversa. Por isso a ausencia e dita com todas as letras, em vez
 * de deixar o card em branco.
 */
export function ChavePixCard({ action, initialState, chave, podeConfigurar }: Props) {
  const [state, formAction, pendente] = useActionState(action, initialState);
  const [idempotencia, setIdempotencia] = useState(() => crypto.randomUUID());
  const enviar = (dados: FormData) => {
    formAction(dados);
    setIdempotencia(crypto.randomUUID());
  };

  const atual = state.kind === "success" ? state.chave : chave;

  return (
    <div className="grid gap-4 rounded-xl border border-border bg-card p-5">
      <div className="grid gap-1">
        <h2 className="font-semibold">Sua chave Pix (sem taxa)</h2>
        <p className="text-sm text-muted-foreground">
          O agente envia esta chave ao devedor e pede o comprovante. Voce confere na sua conta e
          autoriza o lancamento — sem taxa de provedor.
        </p>
        <p className="text-sm" data-testid="chave-pix-estado">
          {atual.configurada ? (
            <>
              Chave atual: <span className="font-medium">{atual.valor}</span>
              {atual.tipo ? ` (${ROTULO[atual.tipo] ?? atual.tipo})` : null}
              {atual.favorecido ? ` — ${atual.favorecido}` : null}
            </>
          ) : (
            "Nenhuma chave cadastrada — o agente nao oferece Pix ate cadastrar uma."
          )}
        </p>
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

      {podeConfigurar ? (
        <form action={enviar} className="grid max-w-md gap-2">
          <input name="idempotency_key" type="hidden" value={idempotencia} />
          <Label htmlFor="chave-pix-tipo">Tipo da chave</Label>
          <select
            className="h-9 rounded-md border border-input bg-background px-3 text-sm"
            defaultValue={atual.tipo ?? "telefone"}
            id="chave-pix-tipo"
            name="tipo"
          >
            {TIPOS_CHAVE_PIX.map((tipo) => (
              <option key={tipo} value={tipo}>{ROTULO[tipo]}</option>
            ))}
          </select>
          <Label htmlFor="chave-pix-valor">Chave</Label>
          <Input defaultValue={atual.valor ?? ""} id="chave-pix-valor" name="valor" required />
          <Label htmlFor="chave-pix-favorecido">Nome do favorecido</Label>
          <Input defaultValue={atual.favorecido ?? ""} id="chave-pix-favorecido" name="favorecido" required />
          <p className="text-xs text-muted-foreground">
            O devedor ve este nome ao pagar. Confira: chave errada so aparece quando alguem tenta.
          </p>
          <Button className="justify-self-start" disabled={pendente} type="submit">
            {pendente ? "Salvando..." : "Salvar chave"}
          </Button>
        </form>
      ) : null}
    </div>
  );
}
