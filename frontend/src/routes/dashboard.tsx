import { createFileRoute, Link } from "@tanstack/react-router";
import {
  Bell,
  UploadCloud,
  Library,
  ArrowRight,
  FileText,
  Users,
  Calendar,
  Tag,
  Clock,
  BookOpen,
} from "lucide-react";
import { Sidebar } from "@/components/app/Sidebar";
import { SearchInput } from "@/components/app/SearchInput";
import { SectionCard } from "@/components/app/SectionCard";
import { StatusBadge } from "@/components/app/StatusBadge";
import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";
import { getPapers, type PaperResponse } from "@/lib/api";

export const Route = createFileRoute("/dashboard")({
  head: () => ({
    meta: [
      { title: "Overview · PaperLens" },
      {
        name: "description",
        content:
          "Your research workspace overview: upload papers, review recent work, and continue reading in PaperLens.",
      },
      { property: "og:title", content: "Overview · PaperLens" },
      {
        property: "og:description",
        content: "Your research workspace overview in PaperLens.",
      },
    ],
  }),
  component: DashboardPage,
});

function formatDate(iso: string) {
  if (!iso) return "Recently analyzed";
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function DashboardPage() {
  const [open, setOpen] = useState(false);
  const [papers, setPapers] = useState<PaperResponse[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getPapers()
      .then((data) => setPapers(data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const totalPapers = papers.length;
  const readyPapers = papers.filter((p) => p.status === "READY").length;
  const processingPapers = papers.filter((p) => p.status === "PROCESSING").length;
  const recentPapers = papers.slice(0, 3);
  const lastPaper = papers[0];

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="fixed inset-y-0 left-0 z-30 hidden w-60 md:block">
        <Sidebar />
      </div>

      <div
        className={cn(
          "fixed inset-0 z-40 md:hidden",
          open ? "pointer-events-auto" : "pointer-events-none",
        )}
        aria-hidden={!open}
      >
        <div
          onClick={() => setOpen(false)}
          className={cn(
            "absolute inset-0 bg-foreground/40 transition-opacity",
            open ? "opacity-100" : "opacity-0",
          )}
        />
        <div
          className={cn(
            "absolute inset-y-0 left-0 w-64 transition-transform",
            open ? "translate-x-0" : "-translate-x-full",
          )}
        >
          <Sidebar onNavigate={() => setOpen(false)} />
        </div>
      </div>

      <div className="md:pl-60">
        <DashboardHeader onOpenSidebar={() => setOpen(true)} />

        <main className="mx-auto w-full max-w-6xl px-4 pb-16 md:px-8">
          <UploadSection />
          <RecentPapersSection recentPapers={recentPapers} loading={loading} />

          <div className="mt-10 grid gap-6 lg:grid-cols-3">
            <div className="lg:col-span-2">
              <ContinueExploring lastPaper={lastPaper} />
            </div>
            <ResearchSnapshot
              total={totalPapers}
              ready={readyPapers}
              processing={processingPapers}
            />
          </div>
        </main>
      </div>
    </div>
  );
}

function DashboardHeader({ onOpenSidebar }: { onOpenSidebar: () => void }) {
  return (
    <header className="border-b border-border bg-background/80 backdrop-blur">
      <div className="mx-auto grid max-w-6xl grid-cols-[minmax(0,1fr)_auto] items-start gap-4 px-4 py-8 md:grid-cols-[minmax(0,1fr)_auto] md:px-8 md:py-10">
        <div className="flex min-w-0 items-start gap-3">
          <button
            type="button"
            onClick={onOpenSidebar}
            aria-label="Open navigation"
            className="mt-1 grid h-9 w-9 shrink-0 place-items-center rounded-md border border-border text-foreground md:hidden"
          >
            <BookOpen className="h-4 w-4" />
          </button>
          <div className="min-w-0">
            <div className="text-[0.68rem] font-medium uppercase tracking-[0.16em] text-muted-foreground">
              Workspace
            </div>
            <h1 className="mt-1 font-serif-editorial text-3xl leading-tight text-foreground md:text-4xl">
              Welcome back, Researcher.
            </h1>
            <p className="mt-2 max-w-xl text-sm text-muted-foreground md:text-[15px]">
              Understand your papers faster. Explore, question, and extract grounded findings.
            </p>
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-2">
          <div className="hidden md:block md:w-64">
            <SearchInput placeholder="Search papers, authors, sections..." />
          </div>
          <button
            type="button"
            aria-label="Notifications"
            className="grid h-9 w-9 place-items-center rounded-md border border-border text-muted-foreground hover:text-foreground"
          >
            <Bell className="h-4 w-4" />
          </button>
          <div
            aria-label="User Workspace"
            className="grid h-9 w-9 place-items-center rounded-full bg-primary text-xs font-semibold text-primary-foreground"
          >
            PL
          </div>
        </div>
      </div>
    </header>
  );
}

function DocumentMark() {
  return (
    <svg viewBox="0 0 120 140" className="h-32 w-auto text-foreground/25" fill="none" aria-hidden>
      <rect
        x="14"
        y="10"
        width="82"
        height="112"
        rx="2"
        stroke="currentColor"
        strokeWidth="1.2"
        className="fill-background"
      />
      <rect
        x="22"
        y="18"
        width="90"
        height="112"
        rx="2"
        stroke="currentColor"
        strokeWidth="1.2"
        className="fill-surface"
      />
      <path
        d="M32 40h60M32 50h60M32 60h60M32 70h44M32 86h60M32 96h60M32 106h36"
        stroke="currentColor"
        strokeWidth="1"
        strokeLinecap="round"
      />
      <path d="M32 28h28" stroke="var(--terracotta)" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}

function UploadSection() {
  return (
    <section className="mt-10 overflow-hidden rounded-lg border border-border bg-surface">
      <div className="grid gap-8 p-8 md:grid-cols-[1fr_auto] md:items-center md:p-10">
        <div className="max-w-xl">
          <div className="text-[0.68rem] font-medium uppercase tracking-[0.16em] text-muted-foreground">
            Primary action
          </div>
          <h2 className="mt-2 font-serif-editorial text-2xl leading-tight text-foreground md:text-3xl">
            Start with a research paper
          </h2>
          <p className="mt-3 text-sm leading-relaxed text-muted-foreground md:text-[15px]">
            Upload a PDF to generate a structured 10-field summary, extract methodology, and ask
            grounded questions.
          </p>

          <div className="mt-6 flex flex-wrap items-center gap-3">
            <Link
              to="/upload"
              className="inline-flex items-center gap-2 rounded-md bg-primary px-5 py-2.5 text-sm font-medium text-primary-foreground transition hover:opacity-90"
            >
              <UploadCloud className="h-4 w-4" /> Upload PDF
            </Link>
            <Link
              to="/papers"
              className="inline-flex items-center gap-2 rounded-md border border-border bg-background px-5 py-2.5 text-sm font-medium text-foreground transition hover:bg-muted"
            >
              <Library className="h-4 w-4" /> Browse My Papers
            </Link>
          </div>

          <div className="mt-5 flex items-center gap-2 text-xs text-muted-foreground">
            <span className="h-1 w-1 rounded-full bg-muted-foreground/60" />
            PDF up to 20 MB
            <span className="h-1 w-1 rounded-full bg-muted-foreground/60" />
            Structure-aware AI analysis
          </div>
        </div>

        <div className="hidden justify-end md:flex">
          <DocumentMark />
        </div>
      </div>
    </section>
  );
}

function RecentPapersSection({
  recentPapers,
  loading,
}: {
  recentPapers: PaperResponse[];
  loading: boolean;
}) {
  return (
    <section className="mt-12">
      <div className="mb-4 flex items-end justify-between gap-4">
        <div>
          <div className="text-[0.68rem] font-medium uppercase tracking-[0.16em] text-muted-foreground">
            Library
          </div>
          <h2 className="mt-1 font-serif-editorial text-xl text-foreground">Recent papers</h2>
        </div>
        <Link
          to="/papers"
          className="inline-flex items-center gap-1 text-sm text-primary hover:underline"
        >
          View all <ArrowRight className="h-3.5 w-3.5" />
        </Link>
      </div>

      {loading ? (
        <div className="py-12 text-center text-sm text-muted-foreground">
          Loading recent papers...
        </div>
      ) : recentPapers.length === 0 ? (
        <div className="py-12 text-center text-sm text-muted-foreground border border-dashed border-border rounded-lg">
          No papers uploaded yet. Upload your first PDF above.
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-3">
          {recentPapers.map((p) => (
            <RecentPaperCard key={p.id} paper={p} />
          ))}
        </div>
      )}
    </section>
  );
}

function RecentPaperCard({ paper }: { paper: PaperResponse }) {
  const mappedStatus = paper.status.toLowerCase() as "ready" | "processing" | "failed";

  return (
    <article className="flex h-full flex-col rounded-lg border border-border bg-surface p-5 transition hover:border-primary/60">
      <div className="flex items-start justify-between gap-3">
        <div className="grid h-9 w-7 shrink-0 place-items-center rounded-sm border border-border bg-background text-muted-foreground">
          <FileText className="h-3.5 w-3.5" aria-hidden />
        </div>
        <StatusBadge status={mappedStatus} />
      </div>

      <h3 className="mt-4 font-serif-editorial text-[17px] leading-snug text-foreground">
        {paper.title}
      </h3>

      <dl className="mt-3 space-y-1.5 text-xs text-muted-foreground">
        <div className="flex items-center gap-1.5">
          <Users className="h-3 w-3" aria-hidden />
          <span className="truncate">{paper.authors || "Unknown Author"}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <Calendar className="h-3 w-3" aria-hidden />
          <span>{paper.publication_year || "2026"}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <Clock className="h-3 w-3" aria-hidden />
          <span>{formatDate(paper.created_at)}</span>
        </div>
      </dl>

      <div className="mt-auto flex items-center justify-end border-t border-border pt-4">
        <Link
          to="/paper/$id"
          params={{ id: paper.id }}
          className="inline-flex items-center gap-1 text-sm font-medium text-primary hover:underline"
        >
          Open paper <ArrowRight className="h-3.5 w-3.5" />
        </Link>
      </div>
    </article>
  );
}

function ResearchSnapshot({
  total,
  ready,
  processing,
}: {
  total: number;
  ready: number;
  processing: number;
}) {
  return (
    <SectionCard eyebrow="Workspace" title="Research snapshot">
      <ul className="divide-y divide-border">
        <li className="flex items-baseline justify-between py-3">
          <span className="text-sm text-muted-foreground">Total Papers</span>
          <span className="font-serif-editorial text-2xl text-foreground">{total}</span>
        </li>
        <li className="flex items-baseline justify-between py-3">
          <span className="text-sm text-muted-foreground">Ready for Q&A</span>
          <span className="font-serif-editorial text-2xl text-foreground">{ready}</span>
        </li>
        <li className="flex items-baseline justify-between py-3">
          <span className="text-sm text-muted-foreground">Processing</span>
          <span className="font-serif-editorial text-2xl text-foreground">{processing}</span>
        </li>
      </ul>
    </SectionCard>
  );
}

function ContinueExploring({ lastPaper }: { lastPaper?: PaperResponse }) {
  if (!lastPaper) {
    return (
      <SectionCard eyebrow="Get started" title="Pick up where you left off">
        <p className="text-sm text-muted-foreground py-4">
          Upload a paper to begin your research analysis.
        </p>
      </SectionCard>
    );
  }

  return (
    <SectionCard eyebrow="Continue exploring" title="Pick up where you left off">
      <div className="flex flex-col gap-5 md:flex-row md:items-center md:justify-between">
        <div className="flex min-w-0 items-start gap-4">
          <div className="grid h-14 w-11 shrink-0 place-items-center rounded-sm border border-border bg-background text-muted-foreground">
            <FileText className="h-4 w-4" aria-hidden />
          </div>
          <div className="min-w-0">
            <h3 className="font-serif-editorial text-lg leading-snug text-foreground">
              {lastPaper.title}
            </h3>
            <p className="mt-1 text-xs text-muted-foreground">
              Status: {lastPaper.status} ({lastPaper.progress}%)
            </p>
          </div>
        </div>

        <Link
          to="/paper/$id"
          params={{ id: lastPaper.id }}
          className="inline-flex shrink-0 items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition hover:opacity-90"
        >
          Open paper <ArrowRight className="h-4 w-4" />
        </Link>
      </div>
    </SectionCard>
  );
}
