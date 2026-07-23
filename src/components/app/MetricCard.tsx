import type { LucideIcon } from "lucide-react";

interface Props {
  label: string;
  value: string | number;
  delta?: string;
  icon?: LucideIcon;
}

export function MetricCard({ label, value, delta, icon: Icon }: Props) {
  return (
    <div className="rounded-lg border border-border bg-surface p-5">
      <div className="flex items-center justify-between">
        <span className="text-[0.68rem] font-medium uppercase tracking-[0.14em] text-muted-foreground">
          {label}
        </span>
        {Icon && <Icon className="h-4 w-4 text-muted-foreground" aria-hidden />}
      </div>
      <div className="mt-3 flex items-baseline gap-2">
        <span className="font-serif-editorial text-3xl text-foreground">{value}</span>
        {delta && <span className="text-xs text-muted-foreground">{delta}</span>}
      </div>
    </div>
  );
}
