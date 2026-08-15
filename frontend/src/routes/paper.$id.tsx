import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import {
  ArrowLeft,
  BookOpen,
  Send,
  Sparkles,
  Users,
  Calendar,
  FileText,
  AlertTriangle,
  SearchX,
  CheckCircle2,
  Bookmark,
  BarChart3,
  RotateCw,
  X,
  Layers,
  ExternalLink,
} from "lucide-react";
import { TypingIndicator } from "@/components/app/states/Skeletons";
import { AppShell } from "@/components/app/AppShell";
import { SectionCard } from "@/components/app/SectionCard";
import { StatusBadge } from "@/components/app/StatusBadge";
import { PdfReader } from "@/components/app/PdfReader";
import { ErrorState } from "@/components/app/states/StatePanels";
import {
  askPaperQuestion,
  getPaper,
  getPaperAnalysis,
  getPaperContributions,
  getPaperMethodology,
  evaluatePaperBenchmark,
  retryPaperPipeline,
  reanalyzePaper,
  getPaperChatHistory,
  getPaperRecommendations,
  type ContributionExtractionResponse,
  type MethodologyExtractionResponse,
  type PaperAnalysisResponse,
  type PaperResponse,
  type QuestionAnsweringResponse,
  type SourceMetadataItem,
  type EvaluationBenchmarkReport,
  type RecommendedPaper,
} from "@/lib/api";

export const Route = createFileRoute("/paper/$id")({
  component: PaperDetailPage,
});

interface Msg {
  role: "user" | "assistant";
  text: string;
  kind?: "answer" | "no-source" | "error";
  supportScore?: number;
  abstained?: boolean;
  sources?: SourceMetadataItem[];
}

function PaperDetailPage() {
  const { id: paperId } = Route.useParams();
  const navigate = useNavigate();

  const [paper, setPaper] = useState<PaperResponse | null>(null);
  const [analysis, setAnalysis] = useState<PaperAnalysisResponse | null>(null);
  const [methodology, setMethodology] = useState<MethodologyExtractionResponse | null>(null);
  const [contributions, setContributions] = useState<ContributionExtractionResponse | null>(null);
  const [recommendations, setRecommendations] = useState<RecommendedPaper[]>([]);

  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [readerOpen, setReaderOpen] = useState(false);

  // 3-Way RAG Evaluation Benchmark state
  const [evalModalOpen, setEvalModalOpen] = useState(false);
  const [evalLoading, setEvalLoading] = useState(false);
  const [evalReport, setEvalReport] = useState<EvaluationBenchmarkReport | null>(null);
  const [retryLoading, setRetryLoading] = useState(false);
  const [reanalyzeLoading, setReanalyzeLoading] = useState(false);

  const handleRunBenchmark = async () => {
    setEvalModalOpen(true);
    if (!evalReport) {
      setEvalLoading(true);
      try {
        const report = await evaluatePaperBenchmark(paperId);
        setEvalReport(report);
      } catch (err: any) {
        // Handle gracefully
      } finally {
        setEvalLoading(false);
      }
    }
  };

  const handleRetryPipeline = async () => {
    setRetryLoading(true);
    try {
      await retryPaperPipeline(paperId);
      await fetchPaperDetails();
    } catch {
      // Handle gracefully
    } finally {
      setRetryLoading(false);
    }
  };

  const handleReanalyze = async () => {
    setReanalyzeLoading(true);
    try {
      await reanalyzePaper(paperId);
      // Refresh all analysis data after clearing cache
      const [anaData, methData, contribData] = await Promise.allSettled([
        getPaperAnalysis(paperId),
        getPaperMethodology(paperId),
        getPaperContributions(paperId),
      ]);
      if (anaData.status === "fulfilled") setAnalysis(anaData.value);
      if (methData.status === "fulfilled") setMethodology(methData.value);
      if (contribData.status === "fulfilled") setContributions(contribData.value);
    } catch {
      // Handle gracefully
    } finally {
      setReanalyzeLoading(false);
    }
  };

  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [askingStatus, setAskingStatus] = useState<"idle" | "searching" | "preparing">("idle");

  const fetchPaperDetails = async () => {
    setLoading(true);
    setErrorMessage(null);
    try {
      const p = await getPaper(paperId);
      setPaper(p);

      const welcomeMsg: Msg = {
        role: "assistant",
        text: `Hi! I've indexed "${p.title}". Ask me any grounded question about its methodology, results, dataset, or contributions.`,
      };

      // Load past Q&A chat history from database
      let historyMsgs: Msg[] = [];
      try {
        const history = await getPaperChatHistory(paperId);
        historyMsgs = history.flatMap((item) => [
          {
            role: "user" as const,
            text: item.question,
          },
          {
            role: "assistant" as const,
            text: item.answer,
            kind: item.abstained ? ("no-source" as const) : ("answer" as const),
            supportScore: item.support_score,
            abstained: item.abstained,
            sources: item.sources,
          },
        ]);
      } catch (err) {
        console.warn("Failed to load chat history:", err);
      }

      setMessages([welcomeMsg, ...historyMsgs]);

      // Load analysis, methodology, contributions, and Semantic Scholar recommendations in parallel
      const [anaData, methData, contribData, recData] = await Promise.allSettled([
        getPaperAnalysis(paperId),
        getPaperMethodology(paperId),
        getPaperContributions(paperId),
        getPaperRecommendations(paperId, 5),
      ]);

      if (anaData.status === "fulfilled") setAnalysis(anaData.value);
      if (methData.status === "fulfilled") setMethodology(methData.value);
      if (contribData.status === "fulfilled") setContributions(contribData.value);
      if (recData.status === "fulfilled" && recData.value) {
        setRecommendations(recData.value.recommendations || []);
      }
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to load paper details.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPaperDetails();
  }, [paperId]);

  const askAssistant = async (value: string) => {
    setMessages((m) => [...m, { role: "user", text: value }]);
    setAskingStatus("searching");

    setTimeout(() => {
      if (askingStatus !== "idle") setAskingStatus("preparing");
    }, 400);

    try {
      const resp: QuestionAnsweringResponse = await askPaperQuestion(paperId, value);
      setAskingStatus("idle");

      const REFUSAL_TEXT =
        "I couldn't find enough information in the uploaded paper to answer this reliably.";
      const isAbstained = resp.abstained || resp.answer.includes(REFUSAL_TEXT);

      if (isAbstained) {
        setMessages((m) => [
          ...m,
          {
            role: "assistant",
            kind: "no-source",
            text: REFUSAL_TEXT,
            abstained: true,
            supportScore: resp.support_score,
            sources: resp.sources,
          },
        ]);
      } else {
        setMessages((m) => [
          ...m,
          {
            role: "assistant",
            kind: "answer",
            text: resp.answer,
            abstained: false,
            supportScore: resp.support_score,
            sources: resp.sources,
          },
        ]);
      }
    } catch (err: any) {
      setAskingStatus("idle");
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          kind: "error",
          text: err.message || "I couldn't answer that. Please try again in a moment.",
        },
      ]);
    }
  };

  const send = (e: React.FormEvent) => {
    e.preventDefault();
    const value = input.trim();
    if (!value || askingStatus !== "idle") return;
    setInput("");
    askAssistant(value);
  };

  const retryLast = () => {
    const lastUser = [...messages].reverse().find((m) => m.role === "user");
    if (!lastUser) return;
    setMessages((m) => {
      const idx = [...m].reverse().findIndex((x) => x.role === "assistant");
      if (idx < 0) return m;
      const cut = m.length - 1 - idx;
      return m.slice(0, cut);
    });
    askAssistant(lastUser.text);
  };

  if (loading) {
    return (
      <AppShell eyebrow="Reader" title="Loading paper...">
        <div className="py-20 text-center text-sm text-muted-foreground">
          Loading paper details and AI analysis...
        </div>
      </AppShell>
    );
  }

  if (errorMessage || !paper) {
    return (
      <AppShell eyebrow="Reader" title="Error">
        <div className="mt-8">
          <ErrorState
            title="Paper Not Found"
            description={errorMessage || "We couldn't retrieve this paper."}
            onRetry={fetchPaperDetails}
            secondaryLabel="Back to Library"
            onSecondary={() => navigate({ to: "/papers" })}
          />
        </div>
      </AppShell>
    );
  }

  const mappedStatus = paper.status.toLowerCase() as "ready" | "processing" | "failed";

  return (
    <AppShell eyebrow="Paper Reader" title={paper.title}>
      {readerOpen && (
        <PdfReader
          paper={{
            id: paper.id,
            title: paper.title,
            authors: paper.authors ? [paper.authors] : ["Unknown Author"],
            year: paper.publication_year || 2026,
            venue: "Research Paper",
            addedAt: paper.created_at,
            pages: paper.page_count,
            status: mappedStatus,
            abstract: paper.abstract || "",
            tags: ["Structured Analysis"],
            keyContributions: contributions?.contributions.map((c) => c.text) || [],
            methodology: methodology
              ? [methodology.approach || "", methodology.model || ""].filter(Boolean)
              : [],
            results: analysis ? [analysis.summary.key_results] : [],
            citations: 0,
          }}
          onClose={() => setReaderOpen(false)}
        />
      )}

      <div className="flex items-center justify-between gap-3 flex-wrap">
        <Link
          to="/papers"
          className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-3.5 w-3.5" /> Back to library
        </Link>
        <div className="flex items-center gap-2">
          {mappedStatus === "failed" && (
            <button
              onClick={handleRetryPipeline}
              disabled={retryLoading}
              className="inline-flex items-center gap-1.5 rounded-md border border-destructive/40 bg-background px-3 py-1.5 text-sm font-medium text-destructive hover:bg-destructive/10"
            >
              <RotateCw className={`h-3.5 w-3.5 ${retryLoading ? "animate-spin" : ""}`} />
              {retryLoading ? "Retrying..." : "Retry Pipeline"}
            </button>
          )}
          <button
            onClick={handleRunBenchmark}
            className="inline-flex items-center gap-1.5 rounded-md border border-border bg-surface px-3 py-1.5 text-sm font-medium text-foreground hover:bg-muted"
          >
            <BarChart3 className="h-3.5 w-3.5 text-primary" /> RAG Benchmark
          </button>
          <button
            onClick={handleReanalyze}
            disabled={reanalyzeLoading}
            className="inline-flex items-center gap-1.5 rounded-md border border-border bg-surface px-3 py-1.5 text-sm font-medium text-foreground hover:bg-muted"
            title="Clear cached analysis and re-run with LLM"
          >
            <Layers className={`h-3.5 w-3.5 text-primary ${reanalyzeLoading ? "animate-pulse" : ""}`} />
            {reanalyzeLoading ? "Re-analyzing..." : "Re-analyze"}
          </button>
          <button
            onClick={() => setReaderOpen(true)}
            className="inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:opacity-90"
          >
            <BookOpen className="h-3.5 w-3.5" /> Open PDF Reader
          </button>
        </div>
      </div>


      {/* 3-Way RAG Evaluation Benchmark Modal */}
      {evalModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-xs">
          <div className="relative w-full max-w-4xl max-h-[90vh] overflow-y-auto rounded-lg border border-border bg-background p-6 shadow-xl">
            <div className="flex items-center justify-between border-b border-border pb-4 mb-4">
              <div className="flex items-center gap-2.5">
                <div className="grid h-9 w-9 place-items-center rounded-md bg-primary text-primary-foreground">
                  <BarChart3 className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="font-serif-editorial text-xl font-semibold text-foreground">
                    3-Way RAG Evaluation Benchmark Report
                  </h3>
                  <p className="text-xs text-muted-foreground">
                    Baseline RAG vs. Structure-Aware RAG vs. Structure-Aware with RapidFuzz Verification
                  </p>
                </div>
              </div>
              <button
                onClick={() => setEvalModalOpen(false)}
                className="rounded-md p-1 text-muted-foreground hover:text-foreground hover:bg-muted"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {evalLoading ? (
              <div className="py-16 text-center text-sm text-muted-foreground">
                <RotateCw className="h-6 w-6 animate-spin mx-auto mb-2 text-primary" />
                Evaluating retrieval Recall@K, Precision@K, MRR, Grounding Accuracy, and Abstention...
              </div>
            ) : evalReport ? (
              <div className="space-y-6">
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs border border-border">
                    <thead className="bg-muted/50 text-foreground font-semibold">
                      <tr>
                        <th className="p-3 border-b border-border">Configuration</th>
                        <th className="p-3 border-b border-border">Recall@K</th>
                        <th className="p-3 border-b border-border">Precision@K</th>
                        <th className="p-3 border-b border-border">MRR</th>
                        <th className="p-3 border-b border-border">Grounding Acc.</th>
                        <th className="p-3 border-b border-border">Abstention Acc.</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {evalReport.configurations.map((cfg, idx) => (
                        <tr key={idx} className={idx === 2 ? "bg-primary/5 font-medium" : ""}>
                          <td className="p-3 text-foreground flex items-center gap-1.5">
                            {idx === 2 && <CheckCircle2 className="h-3.5 w-3.5 text-primary" />}
                            {cfg.config_name}
                          </td>
                          <td className="p-3">{(cfg.retrieval.recall_at_k * 100).toFixed(1)}%</td>
                          <td className="p-3">{(cfg.retrieval.precision_at_k * 100).toFixed(1)}%</td>
                          <td className="p-3">{cfg.retrieval.mrr.toFixed(3)}</td>
                          <td className="p-3">{(cfg.grounding.evidence_precision * 100).toFixed(1)}%</td>
                          <td className="p-3">{(cfg.abstention.unanswerable_detection * 100).toFixed(1)}%</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                <div className="grid gap-3 sm:grid-cols-3 text-xs">
                  <div className="rounded-md border border-border bg-muted/20 p-3">
                    <span className="font-semibold text-foreground block mb-1">Structure-Aware Boost</span>
                    <span className="text-muted-foreground">Section routing prioritizes relevant chapters and filters out historical surveys.</span>
                  </div>
                  <div className="rounded-md border border-border bg-muted/20 p-3">
                    <span className="font-semibold text-foreground block mb-1">RapidFuzz Citation Verification</span>
                    <span className="text-muted-foreground">Rejects hallucinated quotes (Threshold S &ge; 90) before DB persistence.</span>
                  </div>
                  <div className="rounded-md border border-border bg-muted/20 p-3">
                    <span className="font-semibold text-foreground block mb-1">Controlled Abstention Guard</span>
                    <span className="text-muted-foreground">Safely refuses unanswerable queries when support score &lt; 0.70.</span>
                  </div>
                </div>

                <div className="flex justify-end pt-2">
                  <button
                    onClick={() => setEvalModalOpen(false)}
                    className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90"
                  >
                    Close Benchmark
                  </button>
                </div>
              </div>
            ) : (
              <div className="py-12 text-center text-sm text-muted-foreground">
                Benchmark evaluation failed to load. Please try again.
              </div>
            )}
          </div>
        </div>
      )}

      <div className="mt-4 grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          {/* Header Card */}
          <SectionCard>
            <div className="flex items-start justify-between gap-4">
              <div className="flex items-start gap-4">
                <div className="grid h-14 w-11 shrink-0 place-items-center rounded-sm border border-border bg-background text-muted-foreground">
                  <FileText className="h-4 w-4" aria-hidden />
                </div>
                <div>
                  <h2 className="font-serif-editorial text-2xl leading-tight text-foreground md:text-3xl">
                    {paper.title}
                  </h2>
                  <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted-foreground">
                    {paper.authors && (
                      <span className="inline-flex items-center gap-1.5">
                        <Users className="h-3.5 w-3.5" /> {paper.authors}
                      </span>
                    )}
                    <span className="inline-flex items-center gap-1.5">
                      <Calendar className="h-3.5 w-3.5" /> {paper.publication_year || "2026"}
                    </span>
                    <span>{paper.page_count} pages</span>
                  </div>
                </div>
              </div>
              <StatusBadge status={mappedStatus} />
            </div>
          </SectionCard>

          {/* 10-Field Summary Section */}
          {analysis?.summary && (
            <SectionCard eyebrow="Structured Summary" title="10-Field Paper Analysis">
              <div className="space-y-4 font-serif-editorial text-[15px] leading-relaxed text-foreground/90">
                <div>
                  <h4 className="text-xs font-sans font-medium uppercase tracking-wider text-muted-foreground mb-1">
                    Executive Summary
                  </h4>
                  <p>{analysis.summary.executive_summary}</p>
                </div>
                <div>
                  <h4 className="text-xs font-sans font-medium uppercase tracking-wider text-muted-foreground mb-1">
                    Problem Statement
                  </h4>
                  <p>{analysis.summary.problem_statement}</p>
                </div>
                <div>
                  <h4 className="text-xs font-sans font-medium uppercase tracking-wider text-muted-foreground mb-1">
                    Objective
                  </h4>
                  <p>{analysis.summary.objective}</p>
                </div>
              </div>
            </SectionCard>
          )}

          {/* Key Contributions & Methodology Grid */}
          <div className="grid gap-6 md:grid-cols-2">
            <SectionCard eyebrow="Contributions" title="Key contributions">
              <ul className="space-y-3">
                {contributions && contributions.contributions.length > 0 ? (
                  contributions.contributions.map((c, i) => (
                    <li key={i} className="flex flex-col gap-1 text-sm text-foreground/90">
                      <div className="flex gap-2">
                        <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
                        <span>{c.text}</span>
                      </div>
                      <div className="ml-3.5 text-[11px] text-muted-foreground">
                        [{c.contribution_type}] Page {c.evidence.page} · {c.evidence.section}
                      </div>
                    </li>
                  ))
                ) : (
                  <li className="text-sm text-muted-foreground">
                    No explicit contributions extracted yet.
                  </li>
                )}
              </ul>
            </SectionCard>

            <SectionCard eyebrow="Approach" title="Methodology">
              {methodology ? (
                <div className="space-y-3 text-sm text-foreground/90">
                  <div>
                    <span className="font-medium text-xs text-muted-foreground block">
                      Approach
                    </span>
                    <span>{methodology.approach}</span>
                  </div>
                  <div>
                    <span className="font-medium text-xs text-muted-foreground block">
                      Model Architecture
                    </span>
                    <span>{methodology.model}</span>
                  </div>
                  {methodology.metrics && methodology.metrics.length > 0 && (
                    <div>
                      <span className="font-medium text-xs text-muted-foreground block">
                        Metrics
                      </span>
                      <span className="text-xs">{methodology.metrics.join(", ")}</span>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-sm text-muted-foreground">
                  No methodology details available.
                </div>
              )}
            </SectionCard>
          </div>

          {/* Results Section */}
          {analysis?.summary?.key_results && (
            <SectionCard eyebrow="Findings" title="Key Results">
              <p className="text-sm leading-relaxed text-foreground/90">
                {analysis.summary.key_results}
              </p>
            </SectionCard>
          )}

          {/* Related Reference Papers (Semantic Scholar API) */}
          <SectionCard eyebrow="Discovery" title="Related Research Papers">
            {recommendations.length > 0 ? (
              <div className="space-y-4">
                {recommendations.map((rec, idx) => (
                  <div
                    key={idx}
                    className="rounded-lg border border-border bg-background p-4 shadow-2xs hover:border-primary/40 transition-colors"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <h4 className="font-serif-editorial text-base font-medium text-foreground">
                        {rec.title}
                      </h4>
                      {rec.url && (
                        <a
                          href={rec.url}
                          target="_blank"
                          rel="noreferrer"
                          className="shrink-0 inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
                        >
                          View Paper <ExternalLink className="h-3 w-3" />
                        </a>
                      )}
                    </div>
                    <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
                      {rec.authors && rec.authors.length > 0 && (
                        <span className="inline-flex items-center gap-1">
                          <Users className="h-3 w-3" /> {rec.authors.slice(0, 3).join(", ")}{rec.authors.length > 3 ? " et al." : ""}
                        </span>
                      )}
                      {rec.year && (
                        <span className="inline-flex items-center gap-1">
                          <Calendar className="h-3 w-3" /> {rec.year}
                        </span>
                      )}
                    </div>
                    {rec.abstract && (
                      <p className="mt-2 text-xs leading-relaxed text-muted-foreground line-clamp-3">
                        {rec.abstract}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="py-6 text-center text-xs text-muted-foreground">
                No related papers found for this research topic yet.
              </div>
            )}
          </SectionCard>
        </div>

        {/* Grounded Q&A Assistant Column */}
        <div className="lg:sticky lg:top-20 lg:h-[calc(100vh-6rem)]">
          <SectionCard
            eyebrow="Ask the paper"
            title="Grounded Q&A"
            className="flex h-full flex-col"
          >
            <div className="mb-3 inline-flex w-fit items-center gap-1.5 rounded-full border border-border bg-background px-2.5 py-0.5 text-[11px] text-muted-foreground">
              <Sparkles className="h-3 w-3 text-primary" /> Verified Grounded Evidence
            </div>

            <div className="flex-1 space-y-4 overflow-y-auto pr-1">
              {messages.map((m, i) => {
                if (m.role === "user") {
                  return (
                    <div
                      key={i}
                      className="rounded-md bg-accent p-3 text-sm text-accent-foreground"
                    >
                      {m.text}
                    </div>
                  );
                }

                if (m.kind === "no-source") {
                  return (
                    <div
                      key={i}
                      className="rounded-md border border-dashed border-border bg-background p-3 text-sm"
                    >
                      <div className="flex items-start gap-2 text-foreground">
                        <SearchX
                          className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground"
                          aria-hidden
                        />
                        <div>
                          <div className="font-medium text-destructive">{m.text}</div>
                          <p className="mt-1 text-xs text-muted-foreground">
                            Evidence support score: {((m.supportScore || 0) * 100).toFixed(0)}%. The
                            paper does not contain sufficient factual evidence to verify this claim.
                          </p>
                        </div>
                      </div>
                    </div>
                  );
                }

                if (m.kind === "error") {
                  return (
                    <div
                      key={i}
                      className="rounded-md border border-border bg-background p-3 text-sm"
                    >
                      <div className="flex items-start gap-2">
                        <AlertTriangle
                          className="mt-0.5 h-4 w-4 shrink-0 text-destructive"
                          aria-hidden
                        />
                        <div className="flex-1">
                          <div className="text-foreground">{m.text}</div>
                          <button
                            type="button"
                            onClick={retryLast}
                            className="mt-2 rounded-md border border-border bg-background px-3 py-1 text-xs text-foreground hover:bg-muted"
                          >
                            Retry
                          </button>
                        </div>
                      </div>
                    </div>
                  );
                }

                return (
                  <div
                    key={i}
                    className="rounded-md border border-border bg-background p-3.5 text-sm text-foreground space-y-3"
                  >
                    <div className="flex items-center justify-between border-b border-border/40 pb-2">
                      <span className="inline-flex items-center gap-1 text-[11px] font-medium text-[color:var(--sage)]">
                        <CheckCircle2 className="h-3.5 w-3.5" /> Supported (
                        {((m.supportScore || 0.95) * 100).toFixed(0)}% Score)
                      </span>
                    </div>

                    <div className="leading-relaxed">{m.text}</div>

                    {/* DISPLAY EVIDENCE SOURCES EXACTLY AS RETURNED BY BACKEND */}
                    {m.sources && m.sources.length > 0 && (
                      <div className="mt-3 border-t border-border/40 pt-2 space-y-2">
                        <div className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground flex items-center gap-1">
                          <Bookmark className="h-3 w-3" /> Grounded Evidence Sources (
                          {m.sources.length})
                        </div>
                        {m.sources.map((src, sIdx) => (
                          <div
                            key={sIdx}
                            className="rounded-sm border border-border/60 bg-muted/30 p-2 text-xs"
                          >
                            <div className="flex items-center justify-between font-medium text-foreground text-[11px] mb-1">
                              <span>
                                Page {src.page} · {src.section}
                              </span>
                            </div>
                            <p className="text-[11px] leading-normal text-muted-foreground italic line-clamp-3">
                              "{src.text}"
                            </p>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}

              {askingStatus !== "idle" && (
                <div className="rounded-md border border-border bg-background p-3">
                  <TypingIndicator
                    label={
                      askingStatus === "searching"
                        ? "Searching paper evidence…"
                        : "Generating grounded answer…"
                    }
                  />
                </div>
              )}
            </div>

            <form onSubmit={send} className="mt-4 flex items-center gap-2">
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask about methodology, dataset, results…"
                disabled={askingStatus !== "idle"}
                className="flex-1 rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20 disabled:opacity-60"
              />
              <button
                type="submit"
                aria-label="Send question"
                disabled={askingStatus !== "idle" || !input.trim()}
                className="grid h-9 w-9 place-items-center rounded-md bg-primary text-primary-foreground transition hover:opacity-90 disabled:opacity-50"
              >
                <Send className="h-4 w-4" />
              </button>
            </form>
          </SectionCard>
        </div>
      </div>
    </AppShell>
  );
}
