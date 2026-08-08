import { cn } from "@/lib/utils";

function Bar({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "animate-pulse rounded-sm bg-[color:color-mix(in_oklab,var(--foreground)_8%,transparent)]",
        className,
      )}
    />
  );
}

export function PaperCardSkeleton() {
  return (
    <div className="flex h-full flex-col rounded-lg border border-border bg-surface p-5">
      <div className="flex items-start justify-between">
        <Bar className="h-9 w-7" />
        <Bar className="h-5 w-16 rounded-full" />
      </div>
      <Bar className="mt-5 h-5 w-4/5" />
      <Bar className="mt-2 h-4 w-3/5" />
      <Bar className="mt-3 h-3 w-1/2" />
      <div className="mt-auto flex items-center justify-between pt-6">
        <Bar className="h-4 w-24" />
        <Bar className="h-4 w-14" />
      </div>
    </div>
  );
}

export function MetricSkeleton() {
  return (
    <div className="rounded-lg border border-border bg-surface p-5">
      <Bar className="h-3 w-24" />
      <Bar className="mt-4 h-8 w-16" />
    </div>
  );
}

export function LineSkeleton({ lines = 3 }: { lines?: number }) {
  return (
    <div className="space-y-2.5">
      {Array.from({ length: lines }).map((_, i) => (
        <Bar key={i} className={cn("h-3.5", i === lines - 1 ? "w-2/3" : "w-full")} />
      ))}
    </div>
  );
}

export function PageSkeleton() {
  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-3">
        <MetricSkeleton />
        <MetricSkeleton />
        <MetricSkeleton />
      </div>
      <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
        <PaperCardSkeleton />
        <PaperCardSkeleton />
        <PaperCardSkeleton />
      </div>
    </div>
  );
}

/** Subtle dot-based indicator used while the assistant is thinking. */
export function TypingIndicator({ label = "Searching the paper..." }: { label?: string }) {
  return (
    <div
      role="status"
      aria-live="polite"
      className="inline-flex items-center gap-2.5 rounded-md border border-border bg-background px-3 py-2 text-sm text-muted-foreground"
    >
      <span className="flex gap-1" aria-hidden>
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-primary [animation-delay:-0.3s]" />
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-primary [animation-delay:-0.15s]" />
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-primary" />
      </span>
      <span>{label}</span>
    </div>
  );
}
