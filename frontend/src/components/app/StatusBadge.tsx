import type { PaperStatus } from "@/lib/mock-papers";
import { cn } from "@/lib/utils";

const map: Record<PaperStatus, { label: string; cls: string; dot: string }> = {
  ready: {
    label: "Ready",
    cls: "text-[color:var(--sage)] bg-[color:color-mix(in_oklab,var(--sage)_15%,transparent)]",
    dot: "bg-[color:var(--sage)]",
  },
  processing: {
    label: "Processing",
    cls: "text-[color:var(--ochre)] bg-[color:color-mix(in_oklab,var(--ochre)_18%,transparent)]",
    dot: "bg-[color:var(--ochre)]",
  },
  failed: {
    label: "Failed",
    cls: "text-destructive bg-destructive/10",
    dot: "bg-destructive",
  },
};

export function StatusBadge({ status }: { status: PaperStatus }) {
  const s = map[status];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium",
        s.cls,
      )}
    >
      <span className={cn("h-1.5 w-1.5 rounded-full", s.dot)} />
      {s.label}
    </span>
  );
}
