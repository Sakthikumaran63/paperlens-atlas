import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import {
  FileText,
  UploadCloud,
  X,
  ShieldCheck,
  ArrowRight,
} from "lucide-react";
import { toast } from "sonner";
import { AppShell } from "@/components/app/AppShell";
import { cn } from "@/lib/utils";
import {
  ErrorState,
  ProcessingState,
  SuccessState,
} from "@/components/app/states/StatePanels";

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

const STEPS = [
  "Uploading document",
  "Extracting text",
  "Structuring sections",
  "Preparing semantic index",
  "Ready for analysis",
] as const;

type Phase = "idle" | "selected" | "processing" | "done" | "processing-failed";
type ValidationError = null | "unsupported" | "too-large" | "upload-failed";

interface SelectedFile {
  name: string;
  sizeBytes: number;
  pages: number;
}

function formatSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function UploadPage() {
  const [phase, setPhase] = useState<Phase>("idle");
  const [file, setFile] = useState<SelectedFile | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [error, setError] = useState<ValidationError>(null);
  const [rejectedName, setRejectedName] = useState<string | null>(null);
  const [stepIndex, setStepIndex] = useState(0);
  const [simulateFailure, setSimulateFailure] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const acceptFile = (raw: File | { name: string; size: number; type?: string }) => {
    setError(null);
    setRejectedName(null);
    const size = "size" in raw ? raw.size : 0;
    const type = "type" in raw ? raw.type ?? "" : "";
    const isPdf =
      raw.name.toLowerCase().endsWith(".pdf") || type === "application/pdf";
    if (!isPdf) {
      setError("unsupported");
      setRejectedName(raw.name);
      return;
    }
    if (size > MAX_MB * 1024 * 1024) {
      setError("too-large");
      setRejectedName(raw.name);
      return;
    }
    const pages = Math.max(6, Math.min(60, Math.round((size || 1_200_000) / 45_000)));
    setFile({ name: raw.name, sizeBytes: size || 1_200_000, pages });
    setPhase("selected");
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const dropped = Array.from(e.dataTransfer.files);
    if (dropped.length === 0) {
      acceptFile({ name: "research-paper.pdf", size: 1_800_000, type: "application/pdf" });
    } else {
      acceptFile(dropped[0]);
    }
  };

  const clearAll = () => {
    setFile(null);
    setPhase("idle");
    setStepIndex(0);
    setError(null);
    setRejectedName(null);
    if (inputRef.current) inputRef.current.value = "";
  };

  const startAnalyze = () => {
    setPhase("processing");
    setStepIndex(0);
  };

  // Advance mock processing steps.
  useEffect(() => {
    if (phase !== "processing") return;

    // Fire "uploaded" toast once step 0 completes.
    if (stepIndex === 1) {
      toast.success("Paper uploaded successfully", {
        description: "Your paper is being prepared for analysis.",
        action: file
          ? { label: "View", onClick: () => {/* mock */} }
          : undefined,
      });
    }

    // Simulated failure at "Structuring sections" (index 2)
    if (simulateFailure && stepIndex === 2) {
      const t = setTimeout(() => setPhase("processing-failed"), 900);
      return () => clearTimeout(t);
    }

    if (stepIndex >= STEPS.length - 1) {
      const t = setTimeout(() => setPhase("done"), 700);
      return () => clearTimeout(t);
    }
    const t = setTimeout(() => setStepIndex((i) => i + 1), 900);
    return () => clearTimeout(t);
  }, [phase, stepIndex, simulateFailure, file]);

  const retryProcessing = () => {
    setSimulateFailure(false);
    setStepIndex(0);
    setPhase("processing");
  };

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

        <div className="mt-8">
          {error && (
            <div className="mb-6">
              {error === "unsupported" && (
                <ErrorState
                  compact
                  title="Unsupported file format"
                  description={
                    <>
                      PaperLens currently supports PDF research papers only.
                      {rejectedName && (
                        <>
                          {" "}
                          <span className="text-foreground">{rejectedName}</span> was not accepted.
                        </>
                      )}
                    </>
                  }
                  retryLabel="Choose a PDF"
                  onRetry={() => inputRef.current?.click()}
                  footer={<span>Supported format: PDF</span>}
                />
              )}
              {error === "too-large" && (
                <ErrorState
                  compact
                  title="File is too large"
                  description={`Please upload a PDF smaller than ${MAX_MB} MB.`}
                  retryLabel="Choose Another File"
                  onRetry={() => inputRef.current?.click()}
                />
              )}
              {error === "upload-failed" && (
                <ErrorState
                  compact
                  title="Upload couldn't be completed"
                  description="Something went wrong while uploading your paper. Please try again."
                  retryLabel="Try Again"
                  onRetry={() => file && startAnalyze()}
                  secondaryLabel="Choose Another File"
                  onSecondary={() => inputRef.current?.click()}
                  footer={
                    rejectedName ? (
                      <span>
                        File: <span className="text-foreground">{rejectedName}</span>
                      </span>
                    ) : undefined
                  }
                />
              )}
            </div>
          )}

          {phase === "idle" && !error && (
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

          {phase === "selected" && file && (
            <SelectedCard
              file={file}
              onRemove={clearAll}
              onAnalyze={startAnalyze}
              simulateFailure={simulateFailure}
              onToggleSimulate={setSimulateFailure}
            />
          )}

          {phase === "processing" && file && (
            <div className="rounded-lg border border-border bg-surface p-6">
              <FileHeader file={file} />
              <div className="mt-6 border-t border-border/60 pt-5">
                <ProcessingState steps={STEPS} currentIndex={stepIndex} />
              </div>
            </div>
          )}

          {phase === "processing-failed" && file && (
            <div className="rounded-lg border border-border bg-surface p-6">
              <FileHeader file={file} />
              <div className="mt-6 border-t border-border/60 pt-5">
                <ProcessingState steps={STEPS} currentIndex={stepIndex} failedIndex={2} />
              </div>
              <div className="mt-6 border-t border-border/60 pt-5">
                <h3 className="font-serif-editorial text-lg text-foreground">
                  We couldn't analyze this paper
                </h3>
                <p className="mt-1 text-sm text-muted-foreground">
                  PaperLens was unable to process this document. The PDF may be damaged,
                  scanned, or difficult to parse.
                </p>
                <div className="mt-4 flex flex-col-reverse gap-2 sm:flex-row">
                  <button
                    type="button"
                    onClick={clearAll}
                    className="rounded-md border border-border bg-background px-4 py-2 text-sm text-foreground hover:bg-muted"
                  >
                    Upload Another Paper
                  </button>
                  <button
                    type="button"
                    onClick={retryProcessing}
                    className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
                  >
                    Try Again
                  </button>
                </div>
                <div className="mt-4">
                  <button
                    type="button"
                    onClick={() => toast.success("Thanks — our team will take a look.")}
                    className="text-xs text-muted-foreground underline-offset-2 hover:text-foreground hover:underline"
                  >
                    Report a problem
                  </button>
                </div>
              </div>
            </div>
          )}

          {phase === "done" && file && (
            <SuccessState
              title="Your paper is ready"
              description="PaperLens has finished analyzing your research paper."
              meta={[
                { label: "Document", value: file.name },
                { label: "Pages", value: file.pages },
                { label: "Sections detected", value: 8 },
                { label: "Status", value: "Ready for analysis" },
              ]}
              primary={
                <Link
                  to="/paper/$id"
                  params={{ id: "attention-is-all-you-need" }}
                  className="inline-flex items-center justify-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
                >
                  Open Analysis
                  <ArrowRight className="h-4 w-4" />
                </Link>
              }
              secondary={
                <Link
                  to="/papers"
                  className="inline-flex items-center justify-center rounded-md border border-border bg-background px-4 py-2 text-sm text-foreground hover:bg-muted"
                >
                  View My Papers
                </Link>
              }
            />
          )}

          {phase === "idle" && !error && (
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
        "flex flex-col items-center justify-center rounded-lg border-2 border-dashed bg-surface px-6 py-16 text-center transition-colors",
        dragOver ? "border-primary bg-accent/40" : "border-border hover:border-primary/40",
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

function FileHeader({ file, onRemove }: { file: SelectedFile; onRemove?: () => void }) {
  return (
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
      {onRemove && (
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
  );
}

function SelectedCard({
  file,
  onRemove,
  onAnalyze,
  simulateFailure,
  onToggleSimulate,
}: {
  file: SelectedFile;
  onRemove: () => void;
  onAnalyze: () => void;
  simulateFailure: boolean;
  onToggleSimulate: (v: boolean) => void;
}) {
  return (
    <div className="rounded-lg border border-border bg-surface p-6">
      <FileHeader file={file} onRemove={onRemove} />

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

      <label className="mt-4 flex cursor-pointer items-center gap-2 text-[11px] text-muted-foreground">
        <input
          type="checkbox"
          checked={simulateFailure}
          onChange={(e) => onToggleSimulate(e.target.checked)}
          className="h-3 w-3 accent-[color:var(--terracotta)]"
        />
        <span>Preview processing-failure state (mock)</span>
      </label>
    </div>
  );
}
