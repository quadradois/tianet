"use client";

import Image from "next/image";
import { useRouter } from "next/navigation";
import { startTransition, useActionState, useEffect, useState } from "react";

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
 * Enquanto a renovacao automatica corre, este prazo nunca vence: cada QR e
 * substituido em 20s. Ele governa o RABO — o ultimo QR, depois que o orcamento
 * de renovacoes acabou. E o que faz a aba esquecida parar de consultar o
 * backend, porque o polling de estado segue o QR na tela.
 *
 * Confirmado com o provedor em 2026-09-04: 20s por codigo, 5 codigos por ciclo.
 * Dois minutos cobrem um ciclo inteiro com folga.
 */
const JANELA_PAREAMENTO_MS = 120_000;

/**
 * Vida de UM QR no provedor, e por isso o intervalo da renovacao automatica.
 *
 * **20s, fixo na lib, sem rate limit** — medido no codigo-fonte deles
 * (`docs/whatsapp/2026-09-04-resposta-esclarecimento-evolution.md` secao 2).
 * Renovar e repetir o `POST /instance/connect`, que eles confirmaram ser seguro:
 * nao reinicia o ciclo, nao duplica handler, so re-aponta o webhook. Era por
 * medo dessa chamada que a tela exigia um clique a cada 20s.
 */
const RENOVACAO_QR_MS = 20_000;

/**
 * Quantas renovacoes automaticas antes de devolver o volante ao operador.
 *
 * Quatro renovacoes, e nao cinco: a busca do clique ja e a primeira tentativa, e
 * o ciclo do provedor tem cinco codigos. Sao cinco TENTATIVAS, nao cinco codigos
 * garantidos — uma delas pode voltar sem QR, que e resposta legitima.
 *
 * O limite nao e restricao do provedor (`GET /instance/qr` se autocura depois do
 * 5o) e sim do defeito que ja pegamos uma vez: aba esquecida conversando com o
 * backend para sempre. Esgotado o orcamento, o QR na tela morre pela
 * `JANELA_PAREAMENTO_MS` e o botao reassume.
 */
const RENOVACOES_AUTOMATICAS = 4;

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
 * Os 5s sao do polling de ESTADO, que so pergunta "ja pareou?". Quem renova o QR
 * e o temporizador de `RENOVACAO_QR_MS`, na tela — sao dois relogios com
 * perguntas diferentes.
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
  const [renovacoes, setRenovacoes] = useState(0);

  // **Uma tentativa de pareamento em curso**, e nao "ha QR na tela". A diferenca
  // e um defeito real: quando o provedor responde `200` com `qrcode_base64:
  // null` — que e o caminho NORMAL logo apos o `connect`, nao falha — nao ha QR
  // nenhum, e amarrar o laco ao QR fazia a renovacao nunca comecar. A tela
  // ficava pedindo um clique que o operador nao tinha motivo para dar.
  //
  // `operacao === "conectar"` e o que impede o laco de renascer depois do
  // logout: desconectar tambem devolve sucesso, e sem esse campo o unico sinal
  // era a AUSENCIA da chave `qrcode`.
  const pareando = state.kind === "success" && state.operacao === "conectar" && !conectada;

  // O `!pendente` faz DUAS coisas, e uma delas nao e obvia.
  //
  // A primeira: nenhum temporizador fica armado enquanto uma escrita corre, que
  // e a mesma condicao que desabilita o botao — o debounce que o provedor pediu.
  //
  // A segunda so apareceu quando uma mutacao mostrou que o teste do debounce nao
  // provava nada: a alternancia de `pendente` e o que faz o efeito RODAR DE NOVO
  // depois de cada acao. Se o provedor devolver o mesmo QR duas vezes seguidas —
  // legitimo, o codigo vive 20s —, `qrcode` nao muda, e sem essa alternancia
  // nenhum temporizador novo e armado: o laco morre calado.
  const renovacaoAtiva = pareando && !pendente && renovacoes < RENOVACOES_AUTOMATICAS;

  // O polling para enquanto uma escrita corre, e **nao** durante o laco inteiro.
  //
  // A recomendacao do provedor e literal e estreita (resposta de 2026-09-04,
  // §7.1): *"evitem disparar `connect`/`logout`/`qr` em paralelo para a mesma
  // instancia"*. `status` aparece na lista de handlers que tocam os mapas sem
  // lock, mas fora da recomendacao — ele le o ponteiro, os outros tres mexem
  // nele.
  //
  // Desarmar o intervalo durante todo o laco fecharia tambem essa sobra, e eu
  // cheguei a fazer isso — ao custo de o operador esperar ate 20s para a tela
  // dizer "Conectado" depois de escanear, porque a unica leitura de estado
  // passaria a ser o `revalidatePath` de cada renovacao. Duas jornadas
  // Playwright reprovaram, e estavam certas: o preco e do operador, e a
  // recomendacao do provedor nao pedia isso.
  //
  // ponytail: sobra a janela de um `refresh` JA EM VOO quando a escrita comeca —
  // nao da para cancela-lo do cliente. Fechar exigiria um lock que atravessasse
  // a ida ao servidor; se o provedor puser o `sync.Mutex` por instancia que ele
  // mesmo cogita na §7.1, some sozinha.
  usePollingDePareamento(qrcode !== null && !conectada && !pendente);

  // Efeito no corpo do componente, e nao num hook proprio: um hook receberia a
  // funcao de renovar como prop instavel, e o efeito reiniciaria o temporizador
  // a cada render — que nunca chegaria aos 20s. `formAction` vem do
  // `useActionState` e e estavel; `qrcode` na lista faz cada QR novo ganhar o
  // seu proprio prazo.
  //
  // `startTransition` NAO e adorno: sem ele o despacho AINDA ACONTECE, mas fora
  // do contexto da action — o React 19 reclama no console e `pendente` para de
  // acompanhar a requisicao, o que derrubaria justamente o debounce que o
  // comentario acima promete. O teste reprova por `console.error` para que essa
  // regressao nao volte silenciosa.
  useEffect(() => {
    if (!renovacaoAtiva) return;
    const id = setTimeout(() => {
      setRenovacoes((feitas) => feitas + 1);
      const dados = new FormData();
      dados.set("intent", "conectar");
      startTransition(() => formAction(dados));
    }, RENOVACAO_QR_MS);
    return () => clearTimeout(id);
  }, [renovacaoAtiva, qrcode, formAction]);

  // O clique devolve o orcamento inteiro: e o operador dizendo que ainda esta na
  // frente da tela, que e exatamente o que o limite tenta descobrir.
  const acaoDoOperador = (dados: FormData) => {
    setRenovacoes(0);
    formAction(dados);
  };

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
            <form action={acaoDoOperador}>
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
                {renovacaoAtiva || pendente
                  ? " O codigo se renova sozinho enquanto esta tela estiver aberta."
                  : " A renovacao automatica terminou — toque em Gerar novo QR."}
              </p>
            </div>
          ) : null}

          {podeGerir ? (
            <form action={acaoDoOperador}>
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
