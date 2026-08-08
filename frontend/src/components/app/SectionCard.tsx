import { cn } from "@/lib/utils";
import type { ReactNode } from "react";

interface Props {
  title?: ReactNode;
  eyebrow?: ReactNode;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}

export function SectionCard({ title, eyebrow, action, children, className }: Props) {
  return (
    <section
      className={cn("rounded-lg border border-border bg-surface p-6 shadow-none", className)}
    >
      {(title || eyebrow || action) && (
        <header className="mb-4 flex items-start justify-between gap-4">
          <div className="min-w-0">
            {eyebrow && (
              <div className="mb-1 text-[0.68rem] font-medium uppercase tracking-[0.14em] text-muted-foreground">
                {eyebrow}
              </div>
            )}
            {title && <h2 className="font-serif-editorial text-xl text-foreground">{title}</h2>}
          </div>
          {action && <div className="shrink-0">{action}</div>}
        </header>
      )}
      {children}
    </section>
  );
}
