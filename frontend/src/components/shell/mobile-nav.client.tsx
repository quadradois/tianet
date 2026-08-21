"use client";

import { useEffect, useState, type ReactNode } from "react";
import { usePathname } from "next/navigation";

import { Sheet, SheetBody, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "../ui/sheet";

type MobileNavProps = Readonly<{ children: ReactNode }>;

export function MobileNav({ children }: MobileNavProps) {
  const [open, setOpen] = useState(false);
  const pathname = usePathname();
  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  return (
    <>
      <button
        aria-label="Abrir menu de navegacao"
        aria-expanded={open}
        className="inline-flex min-h-(--size-control) items-center gap-2 rounded-md border border-border bg-background px-3 text-sm font-semibold text-foreground hover:bg-muted lg:hidden"
        onClick={() => setOpen(true)}
        type="button"
      >
        <svg aria-hidden="true" className="size-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
          <path d="M4 6h16M4 12h16M4 18h16" strokeLinecap="round" />
        </svg>
        Menu
      </button>
      <Sheet onOpenChange={setOpen} open={open}>
        <SheetContent aria-label="Navegacao principal" side="left">
          <SheetHeader>
            <SheetTitle>Menu</SheetTitle>
            <SheetDescription>Acesse as areas do sistema.</SheetDescription>
          </SheetHeader>
          <SheetBody>{children}</SheetBody>
        </SheetContent>
      </Sheet>
    </>
  );
}
