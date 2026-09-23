import type { AgentInbox } from "@/lib/agent/agent-policy";

const formatadorData = new Intl.DateTimeFormat("pt-BR", {
  day: "2-digit",
  month: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  timeZone: "America/Sao_Paulo",
});

const ROTULO_CLASSE: Record<string, string> = {
  operadora: "Operadora",
  devedor: "Devedor",
  pre_cadastro: "Pre-cadastro",
};

/**
 * Classe desconhecida aparece crua, nunca como "Pre-cadastro": o fallback
 * anterior rotulava o devedor (IMP-381) como desconhecido, e toda classe nova
 * repetiria o engano em silencio.
 */
function classeRotulo(classe: string): string {
  return ROTULO_CLASSE[classe] ?? classe;
}

/** Tela de operacao do agente (S3, somente leitura, sem Client Component). */
export function AgentScreen({ inbox }: { inbox: AgentInbox }) {
  const recentes = inbox.recentes ?? [];
  return (
    <section className="grid gap-5">
      <header className="grid gap-1">
        <p className="text-sm text-muted-foreground">Operacao assistida</p>
        <h1 className="text-2xl font-semibold tracking-tight">Agente</h1>
        <p className="max-w-2xl text-sm text-muted-foreground">
          Resumo e mensagens recentes da inbox do WhatsApp para triagem. Esta tela nao
          envia mensagens nem altera configuracoes.
        </p>
      </header>

      <div className="grid gap-3 sm:grid-cols-4" role="status" aria-label="Resumo da inbox">
        <div className="rounded-xl border border-border bg-card p-5">
          <p className="text-sm text-muted-foreground">Total recebido</p>
          <p className="mt-1 text-2xl font-semibold">{inbox.total}</p>
        </div>
        <div className="rounded-xl border border-border bg-card p-5">
          <p className="flex items-center gap-2 text-sm text-muted-foreground">
            <span className="size-2.5 rounded-full bg-emerald-600" aria-hidden="true" />
            Operadora
          </p>
          <p className="mt-1 text-2xl font-semibold">{inbox.operadora}</p>
        </div>
        <div className="rounded-xl border border-border bg-card p-5">
          <p className="flex items-center gap-2 text-sm text-muted-foreground">
            <span className="size-2.5 rounded-full bg-sky-600" aria-hidden="true" />
            Devedores
          </p>
          <p className="mt-1 text-2xl font-semibold">{inbox.devedor}</p>
        </div>
        <div className="rounded-xl border border-border bg-card p-5">
          <p className="flex items-center gap-2 text-sm text-muted-foreground">
            <span className="size-2.5 rounded-full bg-muted-foreground" aria-hidden="true" />
            Pre-cadastro
          </p>
          <p className="mt-1 text-2xl font-semibold">{inbox.pre_cadastro}</p>
        </div>
      </div>

      <div className="rounded-xl border border-border bg-card p-5">
        <h2 className="text-base font-semibold">Mensagens recentes</h2>
        {recentes.length === 0 ? (
          <p className="mt-2 text-sm text-muted-foreground" role="status">
            Nenhuma mensagem recebida ainda.
          </p>
        ) : (
          <ul className="mt-3 grid gap-3">
            {recentes.map((entrada) => (
              <li key={entrada.provider_input_id} className="grid gap-1 rounded-lg border border-border p-3">
                <p className="flex flex-wrap items-center gap-2 text-sm">
                  <span className="font-medium">{classeRotulo(entrada.classe)}</span>
                  <span className="text-muted-foreground">{entrada.remetente_normalizado}</span>
                  <span className="text-xs text-muted-foreground">{formatadorData.format(new Date(entrada.recebido_em))}</span>
                </p>
                {entrada.texto ? <p className="text-sm">{entrada.texto}</p> : null}
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
