import Link from "next/link";

import type { OperationalContext } from "../../lib/bff/context.server";

type WhatsAppDisconnectionAlertProps = Readonly<{ whatsapp: OperationalContext["whatsapp"] }>;

const MOMENTO_FORMATADO = new Intl.DateTimeFormat("pt-BR", {
  dateStyle: "medium",
  timeStyle: "short",
  // Fuso fixo: a VPS pode rodar em UTC; a operadora le o horario de Sao Paulo.
  timeZone: "America/Sao_Paulo",
});

/**
 * Banner global de queda do WhatsApp (IMP-370 Slice 3).
 *
 * Server Component de proposito: sem `use client`, sem estado, sem efeito e
 * sem import dinamico. Deriva SOMENTE do contexto operacional persistido —
 * aparece enquanto `alerta_queda_ativa` for verdadeiro e some sozinho na
 * proxima carga do contexto que trouxer a reconexao. Nao ha dispensa manual:
 * nenhum botao de fechar, nenhum estado local, nenhum polling.
 *
 * Acessibilidade: `role="alert"` anuncia a queda a tecnologia assistiva, o
 * estado vai no TEXTO (nao so na cor) e a acao e um link nativo — alcancavel
 * por teclado sem JavaScript.
 */
export function WhatsAppDisconnectionAlert({ whatsapp }: WhatsAppDisconnectionAlertProps) {
  if (!whatsapp.alerta_queda_ativa || typeof whatsapp.queda_detectada_em !== "string") {
    return null;
  }
  const momento = MOMENTO_FORMATADO.format(new Date(whatsapp.queda_detectada_em));
  return (
    <div role="alert" className="border-b border-destructive/40 bg-destructive text-destructive-foreground">
      <div className="mx-auto flex w-full max-w-(--size-content) flex-wrap items-center gap-x-4 gap-y-1 px-5 py-3 sm:px-8 lg:px-10">
        <p className="text-sm">
          <strong className="font-semibold">Conexão do WhatsApp caiu.</strong>
          {" Queda detectada em "}
          <time dateTime={whatsapp.queda_detectada_em}>{momento}</time>
          {". Reconecte para retomar o atendimento."}
        </p>
        <Link
          className="text-sm font-semibold underline underline-offset-4 focus-visible:ring-2 focus-visible:ring-destructive-foreground focus-visible:ring-offset-2 focus-visible:ring-offset-destructive"
          href="/app/whatsapp"
        >
          Abrir conexão do WhatsApp
        </Link>
      </div>
    </div>
  );
}
