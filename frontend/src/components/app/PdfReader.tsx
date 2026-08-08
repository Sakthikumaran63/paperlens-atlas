import { useMemo, useState } from "react";
import {
  X,
  ChevronLeft,
  ChevronRight,
  ZoomIn,
  ZoomOut,
  Search,
  Send,
  Sparkles,
  FileText,
} from "lucide-react";
import type { Paper } from "@/lib/mock-papers";
import { cn } from "@/lib/utils";

interface Props {
  paper: Paper;
  onClose: () => void;
}

interface Citation {
  page: number;
  section: string;
  passage: string;
}

interface Msg {
  role: "user" | "assistant";
  text: string;
  citation?: Citation;
}

const SECTIONS = [
  "1. Introduction",
  "2. Background",
  "3. Method",
  "4. Experiments",
  "5. Results",
  "6. Discussion",
  "7. Conclusion",
];

const LOREM_PARAS = [
  "We investigate a family of architectures that operate directly on structured token sequences without reliance on recurrent state. The proposed formulation separates positional information from content, enabling parallelization across the full sequence during both training and inference.",
  "Prior work has explored a spectrum of inductive biases, ranging from strict locality to fully connected interactions. Each imposes trade-offs between expressivity and optimization stability. Our contribution reframes this trade-off as a property of the attention kernel rather than of the underlying computational graph.",
  "Given an input sequence x = (x1, ..., xn), we compute contextual representations h = f(x; θ) using a stack of L identical layers. Each layer combines a multi-head attention block with a position-wise feed-forward network, both wrapped in residual connections and layer normalization.",
  "The attention operation is defined as a weighted sum over value vectors, with weights derived from a scaled dot-product between queries and keys. This construction admits an efficient batched implementation and remains numerically stable when the dimensionality of the key vectors is large.",
  "Empirically, we observe that the model reaches competitive validation loss within a small fraction of the compute required by comparable recurrent baselines. Ablations indicate that both the residual pathway and the layer normalization placement contribute non-trivially to this efficiency.",
  "Across the benchmark suite, we report consistent gains over the strongest prior baselines. Improvements are most pronounced on tasks that require aggregating information across long spans, which we attribute to the uniform receptive field of the attention operator.",
  "We further evaluate on out-of-distribution splits designed to probe robustness. The proposed model degrades gracefully as the distribution shift grows, suggesting that the learned representations generalize beyond the training regime.",
  "Taken together, these results support the view that carefully designed attention-only architectures are a viable alternative to recurrence for a broad class of sequence modelling problems, and that their scaling properties merit further study.",
];

function pickCitation(paper: Paper, q: string): Citation {
  const lower = q.toLowerCase();
  if (lower.includes("result") || lower.includes("benchmark")) {
    return {
      page: 7,
      section: "5. Results",
      passage:
        paper.results[0] ??
        "Across the benchmark suite, we report consistent gains over the strongest prior baselines.",
    };
  }
  if (lower.includes("method") || lower.includes("how") || lower.includes("architecture")) {
    return {
      page: 3,
      section: "3. Method",
      passage:
        paper.methodology[0] ??
        "Each layer combines a multi-head attention block with a position-wise feed-forward network.",
    };
  }
  return {
    page: 2,
    section: "1. Introduction",
    passage:
      paper.keyContributions[0] ??
      "We propose a simple architecture that separates positional information from content.",
  };
}

export function PdfReader({ paper, onClose }: Props) {
  const totalPages = Math.max(paper.pages, 8);
  const [page, setPage] = useState(1);
  const [zoom, setZoom] = useState(100);
  const [searchOpen, setSearchOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Msg[]>([
    {
      role: "assistant",
      text: `I've indexed "${paper.title}". Ask about its method, results, or contributions and I'll cite the passage.`,
    },
  ]);
  const [activeCitation, setActiveCitation] = useState<Citation | null>({
    page: 3,
    section: "3. Method",
    passage:
      paper.methodology[0] ??
      "Each layer combines a multi-head attention block with a position-wise feed-forward network.",
  });

  const paragraphs = useMemo(() => {
    // Deterministic slice per page
    const start = (page - 1) * 3;
    return [0, 1, 2].map((i) => LOREM_PARAS[(start + i) % LOREM_PARAS.length]);
  }, [page]);

  const sectionForPage = SECTIONS[Math.min(page - 1, SECTIONS.length - 1)];

  const send = (e: React.FormEvent) => {
    e.preventDefault();
    const v = input.trim();
    if (!v) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", text: v }]);
    setTimeout(() => {
      const citation = pickCitation(paper, v);
      setActiveCitation(citation);
      setPage(citation.page);
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          text: `Based on ${citation.section}, ${citation.passage} (mocked answer for the prototype.)`,
          citation,
        },
      ]);
    }, 550);
  };

  const highlightOnThisPage = activeCitation && activeCitation.page === page;

  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-background text-foreground">
      {/* Top toolbar */}
      <div className="flex items-center justify-between gap-3 border-b border-border bg-surface px-3 py-2 md:px-4">
        <div className="flex min-w-0 items-center gap-3">
          <div className="grid h-8 w-6 shrink-0 place-items-center rounded-sm border border-border bg-background text-muted-foreground">
            <FileText className="h-3.5 w-3.5" />
          </div>
          <div className="min-w-0">
            <div className="truncate text-sm font-medium">{paper.title}</div>
            <div className="truncate text-[11px] text-muted-foreground">
              {paper.venue} · {paper.year} · {paper.authors[0]}
              {paper.authors.length > 1 ? ` +${paper.authors.length - 1}` : ""}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-1">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            className="grid h-8 w-8 place-items-center rounded-md border border-border hover:bg-accent"
            aria-label="Previous page"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
          <div className="min-w-[74px] text-center text-xs text-muted-foreground">
            Page <span className="text-foreground">{page}</span> / {totalPages}
          </div>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            className="grid h-8 w-8 place-items-center rounded-md border border-border hover:bg-accent"
            aria-label="Next page"
          >
            <ChevronRight className="h-4 w-4" />
          </button>

          <div className="mx-2 hidden h-5 w-px bg-border sm:block" />

          <button
            onClick={() => setZoom((z) => Math.max(70, z - 10))}
            className="grid h-8 w-8 place-items-center rounded-md border border-border hover:bg-accent"
            aria-label="Zoom out"
          >
            <ZoomOut className="h-4 w-4" />
          </button>
          <div className="hidden min-w-[42px] text-center text-xs text-muted-foreground sm:block">
            {zoom}%
          </div>
          <button
            onClick={() => setZoom((z) => Math.min(160, z + 10))}
            className="grid h-8 w-8 place-items-center rounded-md border border-border hover:bg-accent"
            aria-label="Zoom in"
          >
            <ZoomIn className="h-4 w-4" />
          </button>

          <button
            onClick={() => setSearchOpen((s) => !s)}
            className={cn(
              "grid h-8 w-8 place-items-center rounded-md border border-border hover:bg-accent",
              searchOpen && "bg-accent",
            )}
            aria-label="Search in document"
          >
            <Search className="h-4 w-4" />
          </button>

          <button
            onClick={onClose}
            className="ml-1 inline-flex h-8 items-center gap-1.5 rounded-md border border-border px-2.5 text-xs hover:bg-accent"
            aria-label="Close reader"
          >
            <X className="h-3.5 w-3.5" /> Close
          </button>
        </div>
      </div>

      {searchOpen && (
        <div className="border-b border-border bg-surface px-4 py-2">
          <div className="mx-auto flex max-w-2xl items-center gap-2">
            <Search className="h-3.5 w-3.5 text-muted-foreground" />
            <input
              autoFocus
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search within document..."
              className="flex-1 bg-transparent text-sm placeholder:text-muted-foreground focus:outline-none"
            />
            <span className="text-[11px] text-muted-foreground">{query ? "3 matches" : "—"}</span>
          </div>
        </div>
      )}

      {/* Split area */}
      <div className="grid min-h-0 flex-1 grid-cols-1 lg:grid-cols-[1fr_380px]">
        {/* PDF viewer */}
        <div className="min-h-0 overflow-y-auto bg-[color:var(--muted)]/40 p-4 md:p-8">
          <div
            className="mx-auto rounded-sm border border-border bg-white text-[#1a1918] shadow-sm"
            style={{
              width: `min(100%, ${((8.5 * zoom) / 100) * 96}px)`,
              padding: "56px 64px",
              fontFamily: "'Source Serif 4', Georgia, serif",
              transition: "width 150ms ease",
            }}
          >
            {page === 1 ? (
              <>
                <div className="text-center">
                  <h1 className="text-2xl font-semibold leading-tight md:text-[26px]">
                    {paper.title}
                  </h1>
                  <div className="mt-4 text-[13px] text-neutral-700">
                    {paper.authors.join(" · ")}
                  </div>
                  <div className="mt-1 text-[11px] uppercase tracking-widest text-neutral-500">
                    {paper.venue} {paper.year}
                  </div>
                </div>
                <div className="mx-auto mt-8 max-w-[52ch]">
                  <div className="text-center text-[11px] uppercase tracking-widest text-neutral-500">
                    Abstract
                  </div>
                  <p className="mt-2 text-[13px] leading-relaxed text-neutral-800">
                    {paper.abstract}
                  </p>
                </div>
                <div className="mt-10 columns-2 gap-8 text-[12.5px] leading-relaxed text-neutral-800 [column-rule:1px_solid_rgb(0_0_0/0.06)]">
                  <h2 className="mb-2 text-[13px] font-semibold">1. Introduction</h2>
                  <p className="mb-3">{LOREM_PARAS[0]}</p>
                  <p className="mb-3">{LOREM_PARAS[1]}</p>
                </div>
              </>
            ) : (
              <>
                <div className="mb-4 flex items-baseline justify-between border-b border-neutral-200 pb-2 text-[10px] uppercase tracking-widest text-neutral-500">
                  <span>{paper.title.slice(0, 42)}</span>
                  <span>Page {page}</span>
                </div>
                <h2 className="mb-3 text-[15px] font-semibold text-neutral-900">
                  {sectionForPage}
                </h2>
                <div className="columns-2 gap-8 text-[12.5px] leading-relaxed text-neutral-800 [column-rule:1px_solid_rgb(0_0_0/0.06)]">
                  {paragraphs.map((p, i) => {
                    const shouldHighlight = highlightOnThisPage && i === 1 && activeCitation;
                    return (
                      <p key={i} className="mb-3">
                        {shouldHighlight ? (
                          <>
                            {p.slice(0, 60)}{" "}
                            <mark className="rounded-sm bg-[color:var(--terracotta)]/25 px-0.5 py-[1px] text-neutral-900 ring-1 ring-[color:var(--terracotta)]/40">
                              {activeCitation!.passage}
                            </mark>{" "}
                            {p.slice(60)}
                          </>
                        ) : (
                          p
                        )}
                      </p>
                    );
                  })}
                </div>
              </>
            )}
            <div className="mt-10 text-center text-[10px] text-neutral-400">— {page} —</div>
          </div>
        </div>

        {/* AI assistant */}
        <aside className="flex min-h-0 flex-col border-t border-border bg-surface lg:border-l lg:border-t-0">
          <div className="flex items-center justify-between border-b border-border px-4 py-3">
            <div>
              <div className="text-[10px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
                Assistant
              </div>
              <div className="font-serif-editorial text-base">Ask this paper</div>
            </div>
            <span className="inline-flex items-center gap-1.5 rounded-full border border-border bg-background px-2 py-0.5 text-[11px] text-muted-foreground">
              <Sparkles className="h-3 w-3 text-primary" /> Mock
            </span>
          </div>

          <div className="flex-1 space-y-3 overflow-y-auto p-4">
            {messages.map((m, i) => (
              <div key={i} className="space-y-2">
                <div
                  className={cn(
                    "rounded-md p-3 text-sm",
                    m.role === "assistant"
                      ? "border border-border bg-background text-foreground"
                      : "bg-accent text-accent-foreground",
                  )}
                >
                  {m.text}
                </div>
                {m.citation && (
                  <button
                    onClick={() => {
                      setActiveCitation(m.citation!);
                      setPage(m.citation!.page);
                    }}
                    className="w-full rounded-md border border-border bg-background p-3 text-left text-xs transition hover:border-primary/50"
                  >
                    <div className="mb-1 flex items-center justify-between text-[10px] uppercase tracking-widest text-muted-foreground">
                      <span>Source</span>
                      <span>
                        Page {m.citation.page} · {m.citation.section}
                      </span>
                    </div>
                    <div className="border-l-2 border-[color:var(--terracotta)] pl-2 font-serif-editorial text-[13px] italic text-foreground/90">
                      "{m.citation.passage}"
                    </div>
                  </button>
                )}
              </div>
            ))}
          </div>

          <form onSubmit={send} className="border-t border-border p-3">
            <div className="flex items-center gap-2">
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask about method, results…"
                className="flex-1 rounded-md border border-border bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
              />
              <button
                type="submit"
                aria-label="Send"
                className="grid h-9 w-9 place-items-center rounded-md bg-primary text-primary-foreground hover:opacity-90"
              >
                <Send className="h-4 w-4" />
              </button>
            </div>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {["Summarize the method", "What are the main results?", "Key contributions?"].map(
                (s) => (
                  <button
                    key={s}
                    type="button"
                    onClick={() => setInput(s)}
                    className="rounded-full border border-border px-2 py-0.5 text-[11px] text-muted-foreground hover:bg-accent"
                  >
                    {s}
                  </button>
                ),
              )}
            </div>
          </form>
        </aside>
      </div>
    </div>
  );
}
