import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

interface Props {
  icon?: LucideIcon;
  title: string;
  description?: string;
  action?: ReactNode;
}

export function EmptyState({ icon: Icon, title, description, action }: Props) {
  return (
    <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-border bg-surface/60 px-6 py-16 text-center">
      {Icon && (
        <div className="mb-4 grid h-12 w-12 place-items-center rounded-full border border-border bg-background text-muted-foreground">
          <Icon className="h-5 w-5" aria-hidden />
        </div>
      )}
      <h3 className="font-serif-editorial text-lg text-foreground">{title}</h3>
      {description && (
        <p className="mt-1 max-w-sm text-sm text-muted-foreground">{description}</p>
      )}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}
