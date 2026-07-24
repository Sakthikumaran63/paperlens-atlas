import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import {
  FileText,
  UploadCloud,
  X,
  ShieldCheck,
  Check,
  Loader2,
  ArrowRight,
  CheckCircle2,
} from "lucide-react";
import { AppShell } from "@/components/app/AppShell";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/upload")({
  head: () => ({
    meta: [
      { title: "Analyze a Research Paper · PaperLens" },
      {
        name: "description",
        content:
          "Upload a PDF and PaperLens will structure the document for AI-powered analysis.",
      },
      { property: "og:title", content: "Analyze a Research Paper · PaperLens" },
      {
        property: "og:description",
        content:
          "Upload a PDF and PaperLens will structure the document for AI-powered analysis.",
      },
    ],
  }),
  component: UploadPage,
});

const MAX_MB = 20;

interface SelectedFile {
  name: string;
  sizeBytes: number;
  pages: number;
}

const STEPS = [
  "Uploading document",
  "Extracting text",
  "Structuring sections",
  "Preparing semantic index",
  "Ready for analysis",
] as const;

type Phase = "idle" | "selected" | "processing" | "done";

function formatSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function UploadPage() {
  const [phase, setPhase] = useState<Phase>("idle");
  const [file, setFile] = useState<SelectedFile | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [stepIndex, setStepIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const acceptFile = (raw: File | { name: string; size: number }) => {
    setError(null);
    const size = "size" in raw ? raw.size : 0;
    if (size > MAX_MB * 1024 * 1024) {
      setError(`This file is over the ${MAX_MB} MB limit.`);
      return;
    }
    const name = raw.name.endsWith(".pdf") ? raw.name : `${raw.name}.pdf`;
    // Mock a plausible page count based on size.
    const pages = Math.max(6, Math.min(60, Math.round((size || 1_200_000) / 45_000)));
    setFile({ name, sizeBytes: size || 1_200_000, pages });
    setPhase("selected");
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const dropped = Array.from(e.dataTransfer.files);
    if (dropped.length === 0) {
      acceptFile({ name: "research-paper.pdf", size: 1_800_000 });
    } else {
      acceptFile(dropped[0]);
    }
  };

  const removeFile = () => {
    setFile(null);
    setPhase("idle");
    setStepIndex(0);
    setError(null);
    if (inputRef.current) inputRef.current.value = "";
  };

  const startAnalyze = () => {
    setPhase("processing");
    setStepIndex(0);
  };

  // Advance mock processing steps.
  useEffect(() => {
    if (phase !== "processing") return;
    if (stepIndex >= STEPS.length - 1) {
      const t = setTimeout(() => setPhase("done"), 700);
      return () => clearTimeout(t);
    }
    const t = setTimeout(() => setStepIndex((i) => i + 1), 900);
    return () => clearTimeout(t);
  }, [phase, stepIndex]);

  return (
    <AppShell eyebrow="Upload" title="Analyze a research paper">
      <div className="mx-auto max-w-3xl">
        <header className="text-center sm:text-left">
          <h1 className="font-serif-editorial text-3xl leading-tight text-foreground">
            Analyze a research paper
          </h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Upload a PDF and PaperLens will structure the document for AI-powered analysis.
          </p>
        </header>

        <div className="mt-8">
          {phase === "idle" && (
            <DropZone
              dragOver={dragOver}
              onDragOver={(e) => {
                e.preventDefault();
                setDragOver(true);
              }}
              onDragLeave={() => setDragOver(false)}
              onDrop={onDrop}
              onChoose={() => inputRef.current?.click()}
            />
          )}

          {phase !== "idle" && file && (
            <FilePreview
              file={file}
              phase={phase}
              stepIndex={stepIndex}
              onRemove={removeFile}
              onAnalyze={startAnalyze}
            />
          )}

          <input
            ref={inputRef}
            type="file"
            accept="application/pdf"
            className="sr-only"
            onChange={(e) => {
              const list = Array.from(e.target.files ?? []);
              if (list[0]) acceptFile(list[0]);
              e.currentTarget.value = "";
            }}
          />

          {error && (
            <p className="mt-3 text-sm text-destructive" role="alert">
              {error}
            </p>
          )}

          {phase === "idle" && (
            <p className="mt-4 flex items-center justify-center gap-2 text-xs text-muted-foreground">
              <ShieldCheck className="h-3.5 w-3.5" aria-hidden />
              Your document is processed securely and is only used for analysis within your
              workspace.
            </p>
          )}
        </div>
      </div>
    </AppShell>
  );
}

interface DropProps {
  dragOver: boolean;
  onDragOver: (e: React.DragEvent) => void;
  onDragLeave: () => void;
  onDrop: (e: React.DragEvent) => void;
  onChoose: () => void;
}

function DropZone({ dragOver, onDragOver, onDragLeave, onDrop, onChoose }: DropProps) {
  return (
    <div
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
      className={cn(
        "flex flex-col items-center justify-center rounded-xl border-2 border-dashed bg-surface px-6 py-16 text-center transition",
        dragOver ? "border-primary bg-accent/50" : "border-border",
      )}
    >
      <div className="grid h-14 w-14 place-items-center rounded-full border border-border bg-background text-primary">
        <FileText className="h-6 w-6" aria-hidden strokeWidth={1.5} />
      </div>
      <h2 className="mt-5 font-serif-editorial text-xl text-foreground">
        Drop your research paper here
      </h2>
      <p className="mt-1 text-sm text-muted-foreground">
        or choose a PDF from your device
      </p>

      <button
        type="button"
        onClick={onChoose}
        className="mt-6 inline-flex items-center gap-2 rounded-md bg-primary px-5 py-2.5 text-sm font-medium text-primary-foreground transition hover:bg-primary/90"
      >
        <UploadCloud className="h-4 w-4" />
        Choose PDF
      </button>

      <div className="mt-6 flex items-center gap-4 text-[11px] uppercase tracking-wider text-muted-foreground">
        <span>Format · PDF</span>
        <span className="opacity-40">•</span>
        <span>Max {MAX_MB} MB</span>
      </div>
    </div>
  );
}

interface PreviewProps {
  file: SelectedFile;
  phase: Phase;
  stepIndex: number;
  onRemove: () => void;
  onAnalyze: () => void;
}

function FilePreview({ file, phase, stepIndex, onRemove, onAnalyze }: PreviewProps) {
  const isProcessing = phase === "processing";
  const isDone = phase === "done";

  return (
    <div className="rounded-xl border border-border bg-surface p-6">
      <div className="flex items-start gap-4">
        <div className="grid h-12 w-10 shrink-0 place-items-center rounded border border-border bg-background text-muted-foreground">
          <FileText className="h-4 w-4" aria-hidden />
        </div>
        <div className="min-w-0 flex-1">
          <div className="truncate font-serif-editorial text-lg text-foreground">
            {file.name}
          </div>
          <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
            <span>{formatSize(file.sizeBytes)}</span>
            <span className="opacity-40">·</span>
            <span>{file.pages} pages</span>
            <span className="opacity-40">·</span>
            <span>PDF</span>
          </div>
        </div>
        {phase === "selected" && (
          <button
            type="button"
            onClick={onRemove}
            aria-label="Remove file"
            className="rounded-md p-1.5 text-muted-foreground hover:bg-background hover:text-foreground"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>

      {phase === "selected" && (
        <div className="mt-6 flex flex-col-reverse items-stretch gap-3 border-t border-border/60 pt-5 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="font-serif-editorial text-base text-foreground">
              Ready to analyze
            </div>
            <p className="text-xs text-muted-foreground">
              PaperLens will structure the document into sections for analysis.
            </p>
          </div>
          <button
            type="button"
            onClick={onAnalyze}
            className="inline-flex items-center justify-center gap-2 rounded-md bg-primary px-5 py-2.5 text-sm font-medium text-primary-foreground transition hover:bg-primary/90"
          >
            Analyze Paper
            <ArrowRight className="h-4 w-4" />
          </button>
        </div>
      )}

      {(isProcessing || isDone) && (
        <ProcessingTimeline stepIndex={isDone ? STEPS.length - 1 : stepIndex} done={isDone} />
      )}

      {isDone && (
        <div className="mt-6 flex flex-col items-start gap-3 rounded-lg border border-border bg-background p-5 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <span className="grid h-9 w-9 place-items-center rounded-full bg-accent text-primary">
              <CheckCircle2 className="h-5 w-5" />
            </span>
            <div>
              <div className="font-serif-editorial text-base text-foreground">
                Your paper is ready
              </div>
              <p className="text-xs text-muted-foreground">
                Structured sections and semantic index are prepared.
              </p>
            </div>
          </div>
          <Link
            to="/paper/$id"
            params={{ id: "attention-is-all-you-need" }}
            className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition hover:bg-primary/90"
          >
            Open Analysis
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      )}
    </div>
  );
}

function ProcessingTimeline({ stepIndex, done }: { stepIndex: number; done: boolean }) {
  return (
    <ol className="mt-6 space-y-4 border-t border-border/60 pt-5">
      {STEPS.map((label, i) => {
        const state: "done" | "active" | "pending" =
          i < stepIndex || done ? "done" : i === stepIndex ? "active" : "pending";
        return (
          <li key={label} className="flex items-center gap-3">
            <span
              className={cn(
                "grid h-6 w-6 shrink-0 place-items-center rounded-full border transition",
                state === "done" && "border-primary bg-primary text-primary-foreground",
                state === "active" && "border-primary text-primary",
                state === "pending" && "border-border text-muted-foreground",
              )}
              aria-hidden
            >
              {state === "done" ? (
                <Check className="h-3.5 w-3.5" />
              ) : state === "active" ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <span className="text-[10px]">{i + 1}</span>
              )}
            </span>
            <span
              className={cn(
                "text-sm transition",
                state === "pending" ? "text-muted-foreground" : "text-foreground",
                state === "active" && "font-medium",
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
