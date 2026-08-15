import type { ComponentProps } from "react";

import { cn } from "../../lib/utils";

function Input({ className, type = "text", ...props }: ComponentProps<"input">) {
  return (
    <input
      className={cn(
        "min-h-(--size-control) w-full min-w-0 rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground shadow-xs placeholder:text-muted-foreground disabled:cursor-not-allowed disabled:bg-muted disabled:opacity-70",
        className,
      )}
      type={type}
      {...props}
    />
  );
}

export { Input };
