"use client";

import Image from "next/image";
import { useRouter } from "next/navigation";
import { useActionState, useEffect } from "react";

import {
  screenState,
  shouldPoll,
  type WhatsAppActionState,
  type WhatsAppConnection,
} from "../../lib/whatsapp/whatsapp-policy";
import { Button } from "../ui/button";

type Action = (state: WhatsAppActionState, formData: FormData) => Promise<WhatsAppActionState>;

type WhatsAppScreenProps = Readonly<{
  connection: WhatsAppConnection;
  connectAction: Action;
  disconnectAction: Action;
  initialState: WhatsAppActionState;
  podeGerir: boolean;
}>;

const INTERVALO_POLLING_MS = 5_000;

/**
 * Pergunta ao servidor se ja pareou, enquanto ha o que esperar.
 *
 * **So roda no estado pendente.** Conectada nao muda sozinha para melhor, e
 * ausente so muda quando alguem clica — sem essa guarda, uma aba esquecida
 * bateria no backend para sempre.
 *
 * `router.refresh()` e nao um fetch proprio, por dois motivos: ele re-renderiza a
 * rota no servidor, entao o SELO da barra lateral atualiza junto (um fetch local
 * deixaria a tela dizendo "conectado" com o selo vermelho ao lado); e preserva
 * `useState`, entao o QR nao pisca a cada volta do laco.
 *
 * O intervalo e maior que a vida do QR (~20s) de proposito: o polling detecta o
 * PAREAMENTO, nao renova o QR. Renovar e clique do operador, que e quem sabe se
 * ja apontou a camera.
 */
function usePollingDePareamento(ativo: boolean) {
  const router = useRouter();
  useEffect(() => {
    if (!ativo) return;
    const id = setInterval(() => router.refresh(), INTERVALO_POLLING_MS);
    return () => clearInterval(id);
  }, [ativo, router]);
}

function Aviso({ state }: Readonly<{ state: WhatsAppActionState }>) {
  if (state.kind === "idle") return null;
  const problema = state.kind === "problem";
  return (
    <p
      className={problema ? "rounded-md border border-destructive/40 bg-destructive/5 p-3 text-sm" : "rounded-md border border-border bg-muted/40 p-3 text-sm"}
      role={problema ? "alert" : "status"}
    >
      {state.message}
      {/* Correlation ID sempre visivel no erro: e o que liga a reclamacao da
          operadora ao log do servidor. Sem ele, "deu erro" nao investiga nada. */}
      {problema ? <span className="mt-1 block text-xs text-muted-foreground">Correlation ID: {state.correlationId}</span> : null}
    </p>
  );
}

export function WhatsAppScreen({ connection, connectAction, disconnectAction, initialState, podeGerir }: WhatsAppScreenProps) {
  const [connectState, connectFormAction, conectando] = useActionState(connectAction, initialState);
  const [disconnectState, disconnectFormAction, desconectando] = useActionState(disconnectAction, initialState);
  const estado = screenState(connection);
  usePollingDePareamento(shouldPoll(estado));

  // O QR vem da ACAO, nunca da consulta — ele e credencial e sai apenas do
  // `POST`, protegido por `whatsapp.conexao.gerir` (IMP-368).
  const qrcode = connectState.kind === "success" ? connectState.qrcode : null;

  return (
    <section className="grid gap-5">
      <header className="grid gap-1">
        <h1 className="text-xl font-semibold">Conexao do WhatsApp</h1>
        <p className="text-sm text-muted-foreground">
          O canal por onde a operacao fala com os devedores. Comprovantes e avisos saem por aqui.
        </p>
      </header>

      {estado === "conectada" ? (
        <div className="grid gap-4 rounded-xl border border-border bg-card p-5">
          <div className="grid gap-1">
            <p className="flex items-center gap-2 font-semibold">
              <span aria-hidden="true" className="size-2.5 rounded-full bg-emerald-600" />
              Conectado
            </p>
            {/* Numero e nome sao COISAS DIFERENTES: o telefone da conta e o push
                name. Rotular um como o outro foi defeito real, pego em review. */}
            {connection.numero ? <p className="text-sm">Telefone: <span className="font-medium">{connection.numero}</span></p> : null}
            {connection.nome_exibicao ? <p className="text-sm text-muted-foreground">Nome no WhatsApp: {connection.nome_exibicao}</p> : null}
          </div>
          <Aviso state={disconnectState} />
          {podeGerir ? (
            <form action={disconnectFormAction}>
              <Button disabled={desconectando} type="submit" variant="outline">
                {desconectando ? "Desconectando..." : "Desconectar"}
              </Button>
            </form>
          ) : null}
        </div>
      ) : (
        <div className="grid gap-4 rounded-xl border border-destructive/40 bg-destructive/5 p-5">
          <div className="grid gap-1">
            <p className="flex items-center gap-2 font-semibold">
              <span aria-hidden="true" className="size-2.5 rounded-full bg-destructive" />
              Nao conectado
            </p>
            <p className="text-sm text-muted-foreground">
              {estado === "pendente"
                ? "A instancia existe e aguarda a leitura do QR."
                : "Nenhuma instancia de WhatsApp foi criada ainda."}
            </p>
          </div>

          <Aviso state={connectState} />

          {qrcode ? (
            <div className="grid justify-items-start gap-2">
              <Image alt="QR code para parear o WhatsApp" className="rounded-md border border-border bg-white p-2" height={264} src={qrcode} unoptimized width={264} />
              <p className="text-xs text-muted-foreground">
                Abra o WhatsApp no aparelho, va em Aparelhos conectados e aponte a camera.
                O codigo expira em segundos — se passar do tempo, gere outro.
              </p>
            </div>
          ) : null}

          {podeGerir ? (
            <form action={connectFormAction}>
              <Button disabled={conectando} type="submit">
                {conectando ? "Gerando QR..." : qrcode ? "Gerar novo QR" : "Conectar WhatsApp"}
              </Button>
            </form>
          ) : (
            <p className="text-sm text-muted-foreground">Seu acesso permite ver o estado, mas nao conectar.</p>
          )}
        </div>
      )}
    </section>
  );
}
