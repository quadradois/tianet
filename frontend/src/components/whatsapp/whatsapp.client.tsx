"use client";

import Image from "next/image";
import { useRouter } from "next/navigation";
import { useActionState, useEffect, useState } from "react";

import { screenState, type WhatsAppActionState, type WhatsAppConnection } from "../../lib/whatsapp/whatsapp-policy";
import { Button } from "../ui/button";

type Action = (state: WhatsAppActionState, formData: FormData) => Promise<WhatsAppActionState>;

type WhatsAppScreenProps = Readonly<{
  action: Action;
  connection: WhatsAppConnection;
  initialState: WhatsAppActionState;
  podeGerir: boolean;
}>;

const INTERVALO_POLLING_MS = 5_000;

/**
 * Quanto tempo um QR fica de pe na tela antes de ser considerado morto.
 *
 * O contrato do Evolution (secao 4.2) diz que o QR expira em ~20s e o servidor
 * gera ate 5 antes de reiniciar o ciclo — ~100s de janela. Dois minutos cobrem
 * isso com folga.
 *
 * **Numero vindo de documento, nao de medicao.** A confirmacao esta pedida em
 * `docs/whatsapp/SOLICITACAO-ESCLARECIMENTO-EVOLUTION-2026-09-04.md` secao 2.2.
 * Ate ela chegar, o valor erra para o lado seguro: expirar cedo demais custa um
 * clique; nao expirar nunca era o defeito que este limite corrige.
 */
const JANELA_PAREAMENTO_MS = 120_000;

/**
 * Pergunta ao servidor se ja pareou.
 *
 * **Segue o QR na tela, nao o estado da conexao** — e essa distincao e a correcao
 * de um defeito real. Amarrado ao estado, o polling ligava sozinho ao abrir a
 * tela de uma instancia nao pareada, e voltava a ligar depois de "Desconectar"
 * (que preserva a instancia). Uma aba esquecida consultava o backend para sempre,
 * que era exatamente o que o comentario anterior alegava evitar.
 *
 * `router.refresh()` e nao um fetch proprio: re-renderiza a rota no servidor,
 * entao o SELO da barra lateral atualiza junto — um fetch local deixaria a tela
 * dizendo "conectado" com o selo vermelho ao lado. E preserva `useState`, entao o
 * QR nao pisca a cada volta.
 *
 * Os 5s sao do polling de ESTADO, que so pergunta "ja pareou?". Ele nao renova o
 * QR: a renovacao automatica depende de resposta do provedor (secao 2.1 da
 * solicitacao) e ate la quem renova e o operador, no botao.
 */
function usePollingDePareamento(ativo: boolean) {
  const router = useRouter();
  useEffect(() => {
    if (!ativo) return;
    const id = setInterval(() => router.refresh(), INTERVALO_POLLING_MS);
    return () => clearInterval(id);
  }, [ativo, router]);
}

/**
 * Marca UM QR como vencido depois da janela.
 *
 * Guarda qual QR venceu, e nao um booleano: assim um QR novo, gerado depois, nao
 * herda o vencimento do anterior. E o `setState` acontece dentro do `setTimeout`
 * — nunca sincronamente no efeito, o que dispararia render em cascata.
 */
function useQrVigente(qrDaAcao: string | null): string | null {
  const [vencido, setVencido] = useState<string | null>(null);

  useEffect(() => {
    if (!qrDaAcao) return;
    const id = setTimeout(() => setVencido(qrDaAcao), JANELA_PAREAMENTO_MS);
    return () => clearTimeout(id);
  }, [qrDaAcao]);

  return qrDaAcao && qrDaAcao !== vencido ? qrDaAcao : null;
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

export function WhatsAppScreen({ action, connection, initialState, podeGerir }: WhatsAppScreenProps) {
  const [state, formAction, pendente] = useActionState(action, initialState);
  const estado = screenState(connection);
  const conectada = estado === "conectada";

  // O QR vem da ACAO, nunca da consulta — e credencial e sai apenas do `POST`,
  // protegido por `whatsapp.conexao.gerir` (IMP-368). Uma acao so para as duas
  // operacoes garante que desconectar SUBSTITUI este resultado, em vez de deixar
  // um QR velho sobreviver ao logout.
  const qrDaAcao = state.kind === "success" ? state.qrcode ?? null : null;
  const qrcode = useQrVigente(qrDaAcao);

  usePollingDePareamento(qrcode !== null && !conectada);

  return (
    <section className="grid gap-5">
      <header className="grid gap-1">
        <h1 className="text-xl font-semibold">Conexao do WhatsApp</h1>
        <p className="text-sm text-muted-foreground">
          O canal por onde a operacao fala com os devedores. Comprovantes e avisos saem por aqui.
        </p>
      </header>

      {conectada ? (
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
          <Aviso state={state} />
          {podeGerir ? (
            <form action={formAction}>
              <input name="intent" type="hidden" value="desconectar" />
              <Button disabled={pendente} type="submit" variant="outline">
                {pendente ? "Desconectando..." : "Desconectar"}
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

          <Aviso state={state} />

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
            <form action={formAction}>
              <input name="intent" type="hidden" value="conectar" />
              <Button disabled={pendente} type="submit">
                {pendente ? "Gerando QR..." : qrcode ? "Gerar novo QR" : "Conectar WhatsApp"}
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
