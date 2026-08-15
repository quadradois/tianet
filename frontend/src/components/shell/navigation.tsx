import Link from "next/link";

import type { NavigationDestination } from "../../lib/shell/navigation-policy";

type NavigationProps = Readonly<{ items: readonly NavigationDestination[] }>;

export function Navigation({ items }: NavigationProps) {
  return (
    <nav aria-label="Navegacao principal">
      <ul className="grid gap-1">
        {items.map((item) => (
          <li key={item.href}>
            <Link className="block min-h-(--size-control) rounded-md px-3 py-2 text-sm font-semibold hover:bg-muted" href={item.href}>
              {item.label}
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}
