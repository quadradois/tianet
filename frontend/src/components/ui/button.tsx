import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import type { ComponentProps } from "react";

import { cn } from "../../lib/utils";

const buttonVariants = cva(
  "inline-flex min-h-(--size-control) items-center justify-center gap-2 rounded-md px-4 text-sm font-semibold transition-[color,background-color,border-color,box-shadow,transform] duration-(--motion-fast) ease-(--motion-ease) select-none disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50 data-[pressed=true]:translate-y-px",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground shadow-sm hover:bg-primary/90",
        outline: "border border-border bg-background text-foreground hover:bg-muted",
        ghost: "text-foreground hover:bg-muted",
        destructive: "bg-destructive text-destructive-foreground shadow-sm hover:bg-destructive/90",
        success: "bg-success text-success-foreground shadow-sm hover:bg-success/90",
      },
      size: {
        default: "min-h-(--size-control)",
        compact: "min-h-(--size-control-compact) px-3 text-xs",
        large: "min-h-(--size-control-large) px-5 text-base",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
);

type ButtonProps = ComponentProps<"button"> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean;
  };

function Button({ asChild = false, className, size, variant, ...props }: ButtonProps) {
  const Comp = asChild ? Slot : "button";
  return <Comp className={cn(buttonVariants({ size, variant, className }))} {...props} />;
}

export { Button, buttonVariants };
