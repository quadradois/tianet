"use client";

import { useActionState, useState } from "react";

import {
  screenState,
  type MercadoPagoActionState,
  type MercadoPagoConfig,
} from "../../lib/pagamentos/mercadopago-policy";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Label } from "../ui/label";

type Action = (state: MercadoPagoActionState, formData: FormData) => Promise<MercadoPagoActionState>;

type Props = Readonly<{
  action: Action;
  initialState: MercadoPagoActionState;
  config: MercadoPagoConfig;
  podeConfigurar: boolean;
}>;

const TAXA = "0,99% por recebimento";

/**
 * Interruptor do recebimento por Pix (Mercado Pago).
 *
 * A taxa fica visivel ao lado do interruptor **de proposito**: ligar e uma
 * decisao economica, e ela some da cabeca de quem so ve um botao. O caminho
 * sem taxa continua existindo — o devedor paga no Pix da Credora e o agente
 * registra quando ela avisa.
 *
 * Os campos de segredo sao `password` e nascem VAZIOS mesmo quando ja ha
 * credencial: o backend nunca devolve o valor, entao preencher seria mentira.
 */
export function MercadoPagoCard({ action, initialState, config, podeConfigurar }: Props) {
  const [state, formAction, pendente] = useActionState(action, initialState);
  const [chave, setChave] = useState(() => crypto.randomUUID());
  const enviar = (dados: FormData) => {
    formAction(dados);
    setChave(crypto.randomUUID());
  };

  const atual = state.kind === "success" ? state.config : config;
  const estado = screenState(atual);

  return (
    <div className="grid gap-4 rounded-xl border border-border bg-card p-5">
      <div className="grid gap-1">
        <h2 className="font-semibold">Recebimento por Pix (Mercado Pago)</h2>
        <p className="text-sm text-muted-foreground">
          Opcional. Com isto ligado, o devedor recebe um Pix com valor e validade de 60 minutos, e o
          pagamento entra sozinho no sistema. O provedor cobra <strong>{TAXA}</strong>.
        </p>
        <p className="text-sm text-muted-foreground">
          Desligado, o devedor paga no seu Pix e voce avisa o agente, que registra — sem taxa.
        </p>
        <p className="text-sm" data-testid="mercadopago-estado">
          {estado === "ligada" ? (
            <span className="font-medium">Ligado — os devedores podem pedir Pix pela conversa.</span>
          ) : estado === "sem_credencial" ? (
            "Desligado. Informe as credenciais da sua conta Mercado Pago para comecar."
          ) : estado === "sem_teste" ? (
            "Credenciais salvas. Teste antes de ligar."
          ) : (
            "Desligado. Credenciais testadas — pode ligar quando quiser."
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
        <>
          <form action={enviar} className="grid max-w-md gap-2">
            <input name="idempotency_key" type="hidden" value={chave} />
            <input name="intent" type="hidden" value="credenciais" />
            <Label htmlFor="mp-access-token">Access token de producao</Label>
            <Input autoComplete="off" id="mp-access-token" name="credencial" placeholder="APP_USR-..." required type="password" />
            <Label htmlFor="mp-webhook-secret">Segredo do webhook</Label>
            <Input autoComplete="off" id="mp-webhook-secret" name="assinatura" required type="password" />
            <p className="text-xs text-muted-foreground">
              Os dois ficam cifrados e nunca voltam para a tela. Salvar de novo exige testar de novo.
            </p>
            <Button className="justify-self-start" disabled={pendente} type="submit">
              {pendente ? "Salvando..." : "Salvar credenciais"}
            </Button>
          </form>

          <div className="flex flex-wrap gap-2">
            <form action={enviar}>
              <input name="idempotency_key" type="hidden" value={chave} />
              <input name="intent" type="hidden" value="testar" />
              <Button disabled={pendente || estado === "sem_credencial"} type="submit" variant="outline">
                Testar credencial
              </Button>
            </form>
            {atual.habilitado ? (
              <form action={enviar}>
                <input name="idempotency_key" type="hidden" value={chave} />
                <input name="intent" type="hidden" value="desabilitar" />
                <Button disabled={pendente} type="submit" variant="outline">
                  Desligar recebimento
                </Button>
              </form>
            ) : (
              <form action={enviar}>
                <input name="idempotency_key" type="hidden" value={chave} />
                <input name="intent" type="hidden" value="habilitar" />
                <Button disabled={pendente || estado !== "desligada"} type="submit">
                  Ligar recebimento
                </Button>
              </form>
            )}
          </div>
        </>
      ) : null}
    </div>
  );
}
