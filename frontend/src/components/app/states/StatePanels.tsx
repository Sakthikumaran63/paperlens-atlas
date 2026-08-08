import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import { AlertTriangle, CheckCircle2, FileX2, WifiOff, Loader2, Check, X } from "lucide-react";
import { cn } from "@/lib/utils";

type Tone = "neutral" | "warning" | "danger" | "success";

interface StatePanelProps {
  tone?: Tone;
  icon?: LucideIcon;
  eyebrow?: string;
  title: string;
  description?: ReactNode;
  primary?: ReactNode;
  secondary?: ReactNode;
  footer?: ReactNode;
  className?: string;
  compact?: boolean;
}

const toneMap: Record<Tone, { bg: string; icon: string; ring: string }> = {
  neutral: {
    bg: "bg-background",
    icon: "text-muted-foreground",
    ring: "border-border",
  },
  warning: {
    bg: "bg-background",
    icon: "text-[color:var(--ochre)]",
    ring: "border-[color:color-mix(in_oklab,var(--ochre)_35%,var(--border))]",
  },
  danger: {
    bg: "bg-background",
    icon: "text-destructive",
    ring: "border-[color:color-mix(in_oklab,var(--destructive)_25%,var(--border))]",
  },
  success: {
    bg: "bg-background",
    icon: "text-[color:var(--sage)]",
    ring: "border-[color:color-mix(in_oklab,var(--sage)_30%,var(--border))]",
  },
};

/**
 * Editorial state panel used across error, empty, success, and system states.
 * Kept intentionally quiet — no gradients, no color-flooded surfaces.
 */
export function StatePanel({
  tone = "neutral",
  icon: Icon,
  eyebrow,
  title,
  description,
  primary,
  secondary,
  footer,
  className,
  compact,
}: StatePanelProps) {
  const t = toneMap[tone];
  return (
    <div
      role="status"
      className={cn(
        "flex flex-col items-center rounded-lg border border-border bg-surface text-center",
        compact ? "px-6 py-10" : "px-6 py-14",
        className,
      )}
    >
      {Icon && (
        <div
          className={cn("mb-5 grid h-12 w-12 place-items-center rounded-full border", t.bg, t.ring)}
        >
          <Icon className={cn("h-5 w-5", t.icon)} aria-hidden strokeWidth={1.6} />
        </div>
      )}
      {eyebrow && (
        <div className="mb-1 text-[0.68rem] font-medium uppercase tracking-[0.16em] text-muted-foreground">
          {eyebrow}
        </div>
      )}
      <h2 className="font-serif-editorial text-xl text-foreground md:text-2xl">{title}</h2>
      {description && (
        <p className="mt-2 max-w-md text-sm leading-relaxed text-muted-foreground">{description}</p>
      )}
      {(primary || secondary) && (
        <div className="mt-6 flex w-full flex-col items-stretch justify-center gap-2 sm:w-auto sm:flex-row sm:items-center">
          {primary}
          {secondary}
        </div>
      )}
      {footer && <div className="mt-5 text-xs text-muted-foreground">{footer}</div>}
    </div>
  );
}

interface ErrorProps {
  title?: string;
  description?: ReactNode;
  onRetry?: () => void;
  onSecondary?: () => void;
  secondaryLabel?: string;
  retryLabel?: string;
  footer?: ReactNode;
  compact?: boolean;
  className?: string;
}

export function ErrorState({
  title = "Something went wrong",
  description = "We couldn't complete your request. Please try again.",
  onRetry,
  onSecondary,
  secondaryLabel = "Back to Dashboard",
  retryLabel = "Try Again",
  footer,
  compact,
  className,
}: ErrorProps) {
  return (
    <StatePanel
      tone="warning"
      icon={AlertTriangle}
      title={title}
      description={description}
      compact={compact}
      className={className}
      primary={
        onRetry && (
          <button
            type="button"
            onClick={onRetry}
            className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition hover:bg-primary/90"
          >
            {retryLabel}
          </button>
        )
      }
      secondary={
        onSecondary && (
          <button
            type="button"
            onClick={onSecondary}
            className="inline-flex items-center justify-center rounded-md border border-border bg-surface px-4 py-2 text-sm text-foreground transition hover:bg-muted"
          >
            {secondaryLabel}
          </button>
        )
      }
      footer={footer}
    />
  );
}

export function NetworkErrorState({
  onRetry,
  compact,
  className,
}: {
  onRetry?: () => void;
  compact?: boolean;
  className?: string;
}) {
  return (
    <StatePanel
      tone="warning"
      icon={WifiOff}
      title="Connection lost"
      description="We couldn't connect to PaperLens. Check your internet connection and try again."
      compact={compact}
      className={className}
      primary={
        onRetry && (
          <button
            type="button"
            onClick={onRetry}
            className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
          >
            Try Again
          </button>
        )
      }
    />
  );
}

interface SuccessProps {
  title?: string;
  description?: ReactNode;
  meta?: { label: string; value: ReactNode }[];
  primary?: ReactNode;
  secondary?: ReactNode;
  className?: string;
}

export function SuccessState({
  title = "Your paper is ready",
  description = "PaperLens has finished analyzing your research paper.",
  meta,
  primary,
  secondary,
  className,
}: SuccessProps) {
  return (
    <div
      role="status"
      aria-live="polite"
      className={cn("rounded-lg border border-border bg-surface px-6 py-8 text-left", className)}
    >
      <div className="flex items-start gap-4">
        <div className="grid h-10 w-10 shrink-0 place-items-center rounded-full border border-[color:color-mix(in_oklab,var(--sage)_30%,var(--border))] bg-background text-[color:var(--sage)]">
          <CheckCircle2 className="h-5 w-5" strokeWidth={1.6} aria-hidden />
        </div>
        <div className="min-w-0">
          <h2 className="font-serif-editorial text-xl text-foreground">{title}</h2>
          {description && <p className="mt-1 text-sm text-muted-foreground">{description}</p>}
        </div>
      </div>

      {meta && meta.length > 0 && (
        <dl className="mt-6 grid gap-4 border-t border-border/60 pt-5 sm:grid-cols-2">
          {meta.map((m) => (
            <div key={m.label} className="flex flex-col">
              <dt className="text-[0.68rem] font-medium uppercase tracking-[0.14em] text-muted-foreground">
                {m.label}
              </dt>
              <dd className="mt-1 font-serif-editorial text-base text-foreground">{m.value}</dd>
            </div>
          ))}
        </dl>
      )}

      {(primary || secondary) && (
        <div className="mt-6 flex flex-col-reverse gap-2 border-t border-border/60 pt-5 sm:flex-row sm:justify-end">
          {secondary}
          {primary}
        </div>
      )}
    </div>
  );
}

/**
 * Reusable vertical processing timeline with optional per-step failure.
 */
export interface ProcessingStep {
  label: string;
}
type StepState = "done" | "active" | "pending" | "failed";

export function ProcessingState({
  steps,
  currentIndex,
  failedIndex,
  done,
}: {
  steps: readonly string[];
  currentIndex: number;
  failedIndex?: number | null;
  done?: boolean;
}) {
  return (
    <ol className="space-y-4">
      {steps.map((label, i) => {
        let state: StepState = "pending";
        if (failedIndex != null && i === failedIndex) state = "failed";
        else if (failedIndex != null && i < failedIndex) state = "done";
        else if (failedIndex != null && i > failedIndex) state = "pending";
        else if (done || i < currentIndex) state = "done";
        else if (i === currentIndex) state = "active";

        return (
          <li key={label} className="flex items-center gap-3">
            <span
              className={cn(
                "grid h-6 w-6 shrink-0 place-items-center rounded-full border transition",
                state === "done" && "border-primary bg-primary text-primary-foreground",
                state === "active" && "border-primary text-primary",
                state === "pending" && "border-border text-muted-foreground",
                state === "failed" && "border-destructive/60 bg-destructive/10 text-destructive",
              )}
              aria-hidden
            >
              {state === "done" ? (
                <Check className="h-3.5 w-3.5" />
              ) : state === "active" ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : state === "failed" ? (
                <X className="h-3.5 w-3.5" />
              ) : (
                <span className="text-[10px]">{i + 1}</span>
              )}
            </span>
            <span
              className={cn(
                "text-sm transition",
                state === "pending" ? "text-muted-foreground" : "text-foreground",
                state === "active" && "font-medium",
                state === "failed" && "text-destructive",
              )}
            >
              {label}
            </span>
          </li>
        );
      })}
    </ol>
  );
}

/** Minimal document illustration used by 404 & upload — no stock imagery. */
export function DocumentMark({ variant = "plain" }: { variant?: "plain" | "torn" }) {
  return (
    <svg
      viewBox="0 0 96 120"
      role="img"
      aria-label="Document illustration"
      className="h-24 w-20 text-muted-foreground"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.25}
    >
      <path
        d={
          variant === "torn"
            ? "M12 6 h56 l16 16 v52 l-8 -6 -8 8 -10 -8 -10 8 -10 -8 -8 8 -10 -6 V6 Z"
            : "M12 6 h56 l16 16 v92 H12 Z"
        }
      />
      <path d="M68 6 v16 h16" />
      <path d="M24 40 h40 M24 52 h48 M24 64 h32 M24 76 h44 M24 88 h28" strokeOpacity="0.55" />
    </svg>
  );
}

export function UnsupportedFileMark() {
  return (
    <div className="relative">
      <FileX2 className="h-10 w-10 text-[color:var(--ochre)]" strokeWidth={1.5} />
    </div>
  );
}
