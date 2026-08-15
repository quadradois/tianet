import type { ComponentProps } from "react";

import { cn } from "../../lib/utils";

function Card({ className, ...props }: ComponentProps<"section">) {
  return <section className={cn("rounded-xl border border-border bg-card text-card-foreground shadow-sm", className)} {...props} />;
}

function CardHeader({ className, ...props }: ComponentProps<"header">) {
  return <header className={cn("grid gap-1.5 border-b border-border px-5 py-4", className)} {...props} />;
}

function CardTitle({ className, ...props }: ComponentProps<"h2">) {
  return <h2 className={cn("text-base font-semibold tracking-tight", className)} {...props} />;
}

function CardDescription({ className, ...props }: ComponentProps<"p">) {
  return <p className={cn("text-sm leading-6 text-muted-foreground", className)} {...props} />;
}

function CardContent({ className, ...props }: ComponentProps<"div">) {
  return <div className={cn("p-5", className)} {...props} />;
}

export { Card, CardContent, CardDescription, CardHeader, CardTitle };
