import { cva, type VariantProps } from "class-variance-authority";
import type { ComponentProps } from "react";

import { cn } from "../../lib/utils";

const alertVariants = cva("grid gap-1 rounded-lg border px-4 py-3 text-sm", {
  variants: {
    variant: {
      information: "border-information/30 bg-information-subtle text-information-foreground",
      success: "border-success/30 bg-success-subtle text-success-foreground-strong",
      warning: "border-warning/40 bg-warning-subtle text-warning-foreground",
      danger: "border-destructive/30 bg-destructive-subtle text-destructive-foreground-strong",
    },
  },
  defaultVariants: { variant: "information" },
});

type AlertProps = ComponentProps<"div"> & VariantProps<typeof alertVariants>;

function Alert({ className, variant, ...props }: AlertProps) {
  return <div className={cn(alertVariants({ variant }), className)} {...props} />;
}

function AlertTitle({ className, ...props }: ComponentProps<"p">) {
  return <p className={cn("font-semibold", className)} {...props} />;
}

function AlertDescription({ className, ...props }: ComponentProps<"p">) {
  return <p className={cn("leading-6", className)} {...props} />;
}

export { Alert, AlertDescription, AlertTitle, alertVariants };
