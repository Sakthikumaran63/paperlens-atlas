import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { FileText, UploadCloud, X, ShieldCheck, ArrowRight, RotateCw } from "lucide-react";
import { toast } from "sonner";
import { AppShell } from "@/components/app/AppShell";
import { cn } from "@/lib/utils";
import { ErrorState, ProcessingState, SuccessState } from "@/components/app/states/StatePanels";
import {
  getPaperStatus,
  retryPaperPipeline,
  uploadPaper,
  type PaperStatusResponse,
  type PaperUploadResponse,
} from "@/lib/api";

export const Route = createFileRoute("/upload")({
  head: () => ({
    meta: [
      { title: "Analyze a Research Paper · PaperLens" },
      {
        name: "description",
        content: "Upload a PDF and PaperLens will structure the document for AI-powered analysis.",
      },
      { property: "og:title", content: "Analyze a Research Paper · PaperLens" },
      {
        property: "og:description",
        content: "Upload a PDF and PaperLens will structure the document for AI-powered analysis.",
      },
    ],
  }),
  component: UploadPage,
});

const MAX_MB = 20;

const STAGE_LABELS: Record<string, string> = {
  UPLOADING: "Uploading document",
  EXTRACTING: "Extracting text and pages",
  STRUCTURING: "Detecting scientific sections",
  CHUNKING: "Performing structure-aware chunking",
  EMBEDDING: "Generating vector embeddings",
  ANALYZING: "Generating 10-field structured analysis",
  READY: "Ready for analysis",
  FAILED: "Processing failed",
};

const STAGE_INDEXES: Record<string, number> = {
  UPLOADING: 0,
  EXTRACTING: 1,
  STRUCTURING: 2,
  CHUNKING: 3,
  EMBEDDING: 4,
  ANALYZING: 5,
  READY: 6,
  FAILED: -1,
};

const STAGE_STEPS = [
  "Uploading document",
  "Extracting text and pages",
  "Detecting scientific sections",
  "Performing structure-aware chunking",
  "Generating vector embeddings",
  "Generating 10-field structured analysis",
  "Ready for analysis",
];

type Phase = "idle" | "selected" | "uploading" | "processing" | "done" | "processing-failed";


interface SelectedFile {
  raw: File;
  name: string;
  sizeBytes: number;
}

function formatSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function UploadPage() {
  const navigate = useNavigate();
  const [phase, setPhase] = useState<Phase>("idle");
  const [file, setFile] = useState<SelectedFile | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [paperId, setPaperId] = useState<string | null>(null);
  const [statusResponse, setStatusResponse] = useState<PaperStatusResponse | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const acceptFile = (rawFile: File) => {
    setErrorMessage(null);
    const isPdf = rawFile.name.toLowerCase().endsWith(".pdf") || rawFile.type === "application/pdf";
    if (!isPdf) {
      setErrorMessage("Only PDF files are supported.");
      return;
    }
    if (rawFile.size > MAX_MB * 1024 * 1024) {
      setErrorMessage(`File size exceeds limit of ${MAX_MB}MB.`);
      return;
    }
    setFile({ raw: rawFile, name: rawFile.name, sizeBytes: rawFile.size });
    setPhase("selected");
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const dropped = Array.from(e.dataTransfer.files);
    if (dropped.length > 0) {
      acceptFile(dropped[0]);
    }
  };

  const clearAll = () => {
    setFile(null);
    setPhase("idle");
    setErrorMessage(null);
    setPaperId(null);
    setStatusResponse(null);
    if (inputRef.current) inputRef.current.value = "";
  };

  const startUploadAndAnalyze = async () => {
    if (!file) return;
    setPhase("uploading");
    setErrorMessage(null);

    try {
      const uploadResp = await uploadPaper(file.raw);
      setPaperId(uploadResp.paper_id);
      setPhase("processing");
      toast.success("Paper uploaded successfully", {
        description: "Background processing and indexing started.",
      });
    } catch (err: any) {
      setPhase("processing-failed");
      setErrorMessage(err.message || "Failed to upload paper.");
    }
  };

  // Status Polling Effect
  useEffect(() => {
    if (phase !== "processing" || !paperId) return;

    let isMounted = true;
    const interval = setInterval(async () => {
      try {
        const statusData = await getPaperStatus(paperId);
        if (!isMounted) return;

        setStatusResponse(statusData);

        if (statusData.status === "READY") {
          setPhase("done");
          clearInterval(interval);
        } else if (statusData.status === "FAILED") {
          setPhase("processing-failed");
          setErrorMessage(statusData.processing_error || "Paper processing pipeline failed.");
          clearInterval(interval);
        }
      } catch (err: any) {
        if (!isMounted) return;
        setPhase("processing-failed");
        setErrorMessage(err.message || "Error checking paper processing status.");
        clearInterval(interval);
      }
    }, 1500);

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [phase, paperId]);

  const handleRetry = async () => {
    if (!paperId) {
      if (file) startUploadAndAnalyze();
      return;
    }
    setPhase("processing");
    setErrorMessage(null);
    try {
      await retryPaperPipeline(paperId);
      toast.success("Retry pipeline started.");
    } catch (err: any) {
      setPhase("processing-failed");
      setErrorMessage(err.message || "Failed to launch pipeline retry.");
    }
  };

  const stepIndex = statusResponse ? (STAGE_INDEXES[statusResponse.stage] ?? 1) : 0;
  const currentStageLabel = statusResponse
    ? (STAGE_LABELS[statusResponse.stage] ?? "Processing paper...")
    : "Uploading document";
  const progressPercent = statusResponse ? statusResponse.progress : 15;

  return (
    <AppShell eyebrow="Paper Intake" title="Analyze Paper">
      <div className="mx-auto max-w-2xl">
        <header className="border-b border-border/60 pb-5">
          <h1 className="font-serif-editorial text-3xl text-foreground">
            Analyze a Research Paper
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Upload a PDF and PaperLens will detect sections, generate structure-aware chunking,
            create embeddings, and extract key insights.
          </p>
        </header>

        <div className="mt-8 space-y-6">
          {/* Failure State */}
          {phase === "processing-failed" && (
            <ErrorState
              title="Analysis could not be completed"
              description={errorMessage || "We ran into an issue while processing your paper."}
              onRetry={handleRetry}
              secondaryLabel="Choose Another Paper"
              onSecondary={clearAll}
            />
          )}

          {/* Success State */}
          {phase === "done" && paperId && (
            <SuccessState
              title="Paper analysis ready!"
              description="Sections, embeddings, 10-field summary, and grounded Q&A indexes have been successfully created."
              primary={
                <button
                  type="button"
                  onClick={() => navigate({ to: "/paper/$id", params: { id: paperId } })}
                  className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition hover:bg-primary/90"
                >
                  Open Paper <ArrowRight className="h-4 w-4" />
                </button>
              }
              secondary={
                <button
                  type="button"
                  onClick={clearAll}
                  className="rounded-md border border-border px-4 py-2 text-sm font-medium text-foreground hover:bg-muted"
                >
                  Upload Another
                </button>
              }
            />
          )}

          {/* Processing State */}

          {(phase === "uploading" || phase === "processing") && (
            <div className="rounded-lg border border-border bg-surface p-6 space-y-4">
              <div className="text-center">
                <h2 className="font-serif-editorial text-xl text-foreground md:text-2xl">{currentStageLabel}</h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  Processing &quot;{file?.name ?? "PDF"}&quot;. Progress: {progressPercent}%.
                </p>
              </div>
              <div className="max-w-md mx-auto py-2">
                <ProcessingState
                  steps={STAGE_STEPS}
                  currentIndex={stepIndex}
                />
              </div>
              <div className="w-full max-w-md mx-auto space-y-2 pt-2">
                <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
                  <div
                    className="h-full bg-primary transition-all duration-500 ease-out"
                    style={{ width: `${progressPercent}%` }}
                  />
                </div>
                <div className="text-xs text-center text-muted-foreground font-medium">
                  {progressPercent}% Complete
                </div>
              </div>
            </div>
          )}


          {/* File Selected State */}
          {phase === "selected" && file && (
            <div className="rounded-lg border border-border bg-surface p-6">
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-center gap-3">
                  <div className="grid h-10 w-10 shrink-0 place-items-center rounded-md border border-border bg-background text-primary">
                    <FileText className="h-5 w-5" />
                  </div>
                  <div>
                    <h3 className="font-serif-editorial text-lg text-foreground">{file.name}</h3>
                    <p className="text-xs text-muted-foreground">{formatSize(file.sizeBytes)}</p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={clearAll}
                  className="rounded-md p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              <div className="mt-6 flex items-center justify-end gap-3 border-t border-border/40 pt-4">
                <button
                  type="button"
                  onClick={clearAll}
                  className="rounded-md px-4 py-2 text-sm text-muted-foreground hover:text-foreground"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={startUploadAndAnalyze}
                  className="inline-flex items-center gap-2 rounded-md bg-primary px-5 py-2 text-sm font-medium text-primary-foreground transition hover:bg-primary/90"
                >
                  Start Analysis <ArrowRight className="h-4 w-4" />
                </button>
              </div>
            </div>
          )}

          {/* Upload Dropzone (Idle State) */}
          {phase === "idle" && (
            <div
              onDragOver={(e) => {
                e.preventDefault();
                setDragOver(true);
              }}
              onDragLeave={() => setDragOver(false)}
              onDrop={onDrop}
              onClick={() => inputRef.current?.click()}
              className={cn(
                "group relative flex flex-col items-center justify-center rounded-xl border-2 border-dashed p-12 text-center transition cursor-pointer",
                dragOver
                  ? "border-primary bg-primary/5"
                  : "border-border/80 bg-surface hover:border-primary/50 hover:bg-surface/80",
              )}
            >
              <input
                ref={inputRef}
                type="file"
                accept=".pdf,application/pdf"
                className="hidden"
                onChange={(e) => {
                  if (e.target.files?.[0]) acceptFile(e.target.files[0]);
                }}
              />

              <div className="grid h-14 w-14 place-items-center rounded-full border border-border bg-background text-muted-foreground group-hover:text-primary transition">
                <UploadCloud className="h-6 w-6" />
              </div>

              <h2 className="mt-4 font-serif-editorial text-xl text-foreground">
                Drop your research paper PDF here
              </h2>
              <p className="mt-1.5 text-sm text-muted-foreground">
                or click to browse files (PDF up to {MAX_MB}MB)
              </p>

              {errorMessage && (
                <div className="mt-4 text-xs font-medium text-destructive">{errorMessage}</div>
              )}

              <div className="mt-8 flex items-center gap-2 text-xs text-muted-foreground">
                <ShieldCheck className="h-4 w-4 text-[color:var(--sage)]" />
                <span>Isolated workspace processing · Non-source storage safe</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}
