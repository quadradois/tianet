import type { ReactNode } from "react";

type OverflowRegionProps = Readonly<{
  children: ReactNode;
  label: string;
}>;

function OverflowRegion({ children, label }: OverflowRegionProps) {
  return (
    <div
      aria-label={label}
      className="max-w-full overflow-x-auto rounded-lg border border-border bg-background focus-visible:outline-ring"
      role="region"
      tabIndex={0}
    >
      {children}
    </div>
  );
}

export { OverflowRegion };
