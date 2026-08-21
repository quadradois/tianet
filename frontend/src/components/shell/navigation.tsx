"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "../../lib/utils";
import { navigationByGroup, type NavigationDestination } from "../../lib/shell/navigation-policy";

type NavigationProps = Readonly<{ items: readonly NavigationDestination[] }>;

function isActive(pathname: string, href: string): boolean {
  if (pathname === href) return true;
  // Rotas filhas marcam o pai, exceto a raiz /app (para nao acender em todas as subpaginas).
  if (href === "/app") return false;
  return pathname.startsWith(`${href}/`);
}

function Lista({ items, pathname }: NavigationProps & Readonly<{ pathname: string }>) {
  return (
    <ul className="grid gap-1">
      {items.map((item) => {
        const active = isActive(pathname, item.href);
        return (
          <li key={`${item.grupo}-${item.href}-${item.label}`}>
            <Link
              aria-current={active ? "page" : undefined}
              className={cn(
                "block min-h-(--size-control) rounded-md px-3 py-2 text-sm font-semibold hover:bg-muted",
                active && "bg-muted shadow-[inset_3px_0_0_0_var(--ring)]",
              )}
              href={item.href}
            >
              {item.label}
            </Link>
          </li>
        );
      })}
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
  const pathname = usePathname() ?? "/app";
  const principal = navigationByGroup(items, "principal");
  const administracao = navigationByGroup(items, "administracao");
  return (
    <nav aria-label="Navegacao principal">
      <Lista items={principal} pathname={pathname} />
      {administracao.length > 0 ? (
        <details className="mt-3 border-t border-border pt-3">
          <summary className="cursor-pointer px-3 py-2 text-sm font-semibold text-muted-foreground">Mais ferramentas</summary>
          <div className="mt-1">
            <Lista items={administracao} pathname={pathname} />
          </div>
        </details>
      ) : null}
    </nav>
  );
}
