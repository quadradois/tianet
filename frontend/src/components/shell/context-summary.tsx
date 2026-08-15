import type { OperationalContext } from "../../lib/bff/context.server";

type ContextSummaryProps = Readonly<{ context: OperationalContext }>;

export function ContextSummary({ context }: ContextSummaryProps) {
  return (
    <dl className="grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-1" aria-label="Contexto operacional atual">
      <div className="min-w-0">
        <dt className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Tenant</dt>
        <dd className="truncate font-medium" title={context.tenant.nome}>{context.tenant.nome}</dd>
      </div>
      <div className="min-w-0">
        <dt className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Carteira</dt>
        <dd className="truncate font-medium" title={context.carteira_padrao.nome}>{context.carteira_padrao.nome}</dd>
      </div>
      <div className="min-w-0">
        <dt className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Perfil</dt>
        <dd className="truncate font-medium">{context.perfil?.nome ?? "Sem perfil ativo"}</dd>
      </div>
    </dl>
  );
}
