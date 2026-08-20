import Link from "next/link";

import { navigationByGroup, type NavigationDestination } from "../../lib/shell/navigation-policy";

type NavigationProps = Readonly<{ items: readonly NavigationDestination[] }>;

function Lista({ items }: NavigationProps) {
  return (
    <ul className="grid gap-1">
      {items.map((item) => (
        <li key={`${item.grupo}-${item.href}-${item.label}`}>
          <Link className="block min-h-(--size-control) rounded-md px-3 py-2 text-sm font-semibold hover:bg-muted" href={item.href}>
            {item.label}
          </Link>
        </li>
      ))}
    </ul>
  );
}

/**
 * Menu em dois grupos.
 *
 * O dia a dia do Credor fica sempre a vista; o restante existe, continua
 * alcancavel e mantem a permissao, porem recolhido. Nenhum destino foi
 * removido — o que muda e quanto do sistema disputa a primeira olhada.
 */
export function Navigation({ items }: NavigationProps) {
  const principal = navigationByGroup(items, "principal");
  const administracao = navigationByGroup(items, "administracao");
  return (
    <nav aria-label="Navegacao principal">
      <Lista items={principal} />
      {administracao.length > 0 ? (
        <details className="mt-3 border-t border-border pt-3">
          <summary className="cursor-pointer px-3 py-2 text-sm font-semibold text-muted-foreground">Administracao</summary>
          <div className="mt-1">
            <Lista items={administracao} />
          </div>
        </details>
      ) : null}
    </nav>
  );
}
