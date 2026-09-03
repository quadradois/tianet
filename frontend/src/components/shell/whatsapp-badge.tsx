import Link from "next/link";

import { cn } from "../../lib/utils";
import type { OperationalContext } from "../../lib/bff/context.server";

type WhatsAppBadgeProps = Readonly<{ whatsapp: OperationalContext["whatsapp"] }>;

/**
 * Selo de conexao do WhatsApp na barra lateral (IMP-369).
 *
 * Fica FORA do menu de propósito. Conectar o WhatsApp e coisa que se faz uma
 * vez, mas saber que ele caiu importa todo dia — e um item de menu so conta
 * isso para quem for procurar. O selo conta para quem nao estava procurando.
 *
 * **Dois estados, e so dois.** Conectado ou nao conectado. Chegou a existir um
 * terceiro — "instancia criada, aguardando leitura do QR" — e saiu por decisao
 * do fundador: nos dois casos o WhatsApp nao esta funcionando, e um terceiro
 * codigo de cor e sutileza que ninguem le no dia a dia.
 *
 * **Le o ultimo estado CONHECIDO**, vindo do contexto operacional, que ja e
 * buscado em toda pagina. Nao consulta o provedor: sincronizar aqui daria uma
 * chamada externa por navegacao — o defeito que o IMP-368 tirou do QR.
 *
 * O aviso ativo de queda nasce no IMP-370, no worker, que e quem consegue ver a
 * transicao sem alguem estar com a tela aberta.
 */
export function WhatsAppBadge({ whatsapp }: WhatsAppBadgeProps) {
  const conectado = whatsapp.pareada;

  return (
    <Link
      className={cn(
        "flex min-h-(--size-control) items-center gap-2 rounded-md border px-3 py-2 text-sm hover:bg-muted",
        conectado ? "border-border" : "border-destructive/40 bg-destructive/5",
      )}
      href="/app/whatsapp"
    >
      <span
        aria-hidden="true"
        className={cn("size-2.5 shrink-0 rounded-full", conectado ? "bg-emerald-600" : "bg-destructive")}
      />
      <span className="min-w-0">
        {/* O estado vai no TEXTO, e nao so na cor: leitor de tela e daltonico
            precisam da mesma informacao que a bolinha da. */}
        <span className="block font-semibold">{conectado ? "WhatsApp conectado" : "WhatsApp nao conectado"}</span>
        <span className="block truncate text-xs text-muted-foreground">
          {conectado && whatsapp.numero ? whatsapp.numero : "Toque para conectar"}
        </span>
      </span>
    </Link>
  );
}
