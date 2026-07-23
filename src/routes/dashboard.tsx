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
import { useState } from "react";
import { cn } from "@/lib/utils";

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

interface RecentPaper {
  id: string;
  title: string;
  authors: string;
  year: number;
  domain: string;
  analyzed: string;
  status: "ready" | "processing" | "failed";
}

const recentPapers: RecentPaper[] = [
  {
    id: "attention-is-all-you-need",
    title: "Attention Is All You Need",
    authors: "Ashish Vaswani et al.",
    year: 2017,
    domain: "Natural Language Processing",
    analyzed: "Analyzed 2 hours ago",
    status: "ready",
  },
  {
    id: "bert",
    title:
      "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding",
    authors: "Jacob Devlin et al.",
    year: 2019,
    domain: "Language Models",
    analyzed: "Analyzed yesterday",
    status: "ready",
  },
  {
    id: "resnet",
    title: "Deep Residual Learning for Image Recognition",
    authors: "Kaiming He et al.",
    year: 2016,
    domain: "Computer Vision",
    analyzed: "Analyzed 3 days ago",
    status: "processing",
  },
];

const metrics = [
  { label: "Papers analyzed", value: "12" },
  { label: "Questions asked", value: "47" },
  { label: "Reading time saved", value: "8.5 hrs" },
];

const continueReading = {
  id: "attention-is-all-you-need",
  title: "Attention Is All You Need",
  lastSection: "3.2 · Scaled Dot-Product Attention",
  progress: 62,
};

function DashboardPage() {
  const [open, setOpen] = useState(false);

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
          <RecentPapersSection />

          <div className="mt-10 grid gap-6 lg:grid-cols-3">
            <div className="lg:col-span-2">
              <ContinueExploring />
            </div>
            <ResearchSnapshot />
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
              Good morning, Researcher.
            </h1>
            <p className="mt-2 max-w-xl text-sm text-muted-foreground md:text-[15px]">
              Understand your papers faster. Explore, question, and extract what matters.
            </p>
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-2">
          <div className="hidden md:block md:w-64">
            <SearchInput placeholder="Search papers, authors, notes…" />
          </div>
          <button
            type="button"
            aria-label="Notifications"
            className="grid h-9 w-9 place-items-center rounded-md border border-border text-muted-foreground hover:text-foreground"
          >
            <Bell className="h-4 w-4" />
          </button>
          <div
            aria-label="Aria Ren"
            className="grid h-9 w-9 place-items-center rounded-full bg-primary text-xs font-semibold text-primary-foreground"
          >
            AR
          </div>
        </div>
      </div>
    </header>
  );
}

function DocumentMark() {
  // Subtle editorial document illustration (pure SVG, no stock imagery).
  return (
    <svg
      viewBox="0 0 120 140"
      className="h-32 w-auto text-foreground/25"
      fill="none"
      aria-hidden
    >
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
      <path
        d="M32 28h28"
        stroke="var(--terracotta)"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
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
            Upload a PDF to generate a structured summary, extract methodology, and ask
            questions about the paper.
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
            PDF up to 25 MB
            <span className="h-1 w-1 rounded-full bg-muted-foreground/60" />
            English-language papers work best
          </div>
        </div>

        <div className="hidden justify-end md:flex">
          <DocumentMark />
        </div>
      </div>
    </section>
  );
}

function RecentPapersSection() {
  return (
    <section className="mt-12">
      <div className="mb-4 flex items-end justify-between gap-4">
        <div>
          <div className="text-[0.68rem] font-medium uppercase tracking-[0.16em] text-muted-foreground">
            Library
          </div>
          <h2 className="mt-1 font-serif-editorial text-xl text-foreground">
            Recent papers
          </h2>
        </div>
        <Link
          to="/papers"
          className="inline-flex items-center gap-1 text-sm text-primary hover:underline"
        >
          View all <ArrowRight className="h-3.5 w-3.5" />
        </Link>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        {recentPapers.map((p) => (
          <RecentPaperCard key={p.id} paper={p} />
        ))}
      </div>
    </section>
  );
}

function RecentPaperCard({ paper }: { paper: RecentPaper }) {
  return (
    <article className="flex h-full flex-col rounded-lg border border-border bg-surface p-5 transition hover:border-primary/60">
      <div className="flex items-start justify-between gap-3">
        <div className="grid h-9 w-7 shrink-0 place-items-center rounded-sm border border-border bg-background text-muted-foreground">
          <FileText className="h-3.5 w-3.5" aria-hidden />
        </div>
        <StatusBadge status={paper.status} />
      </div>

      <h3 className="mt-4 font-serif-editorial text-[17px] leading-snug text-foreground">
        {paper.title}
      </h3>

      <dl className="mt-3 space-y-1.5 text-xs text-muted-foreground">
        <div className="flex items-center gap-1.5">
          <Users className="h-3 w-3" aria-hidden />
          <span className="truncate">{paper.authors}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <Calendar className="h-3 w-3" aria-hidden />
          <span>{paper.year}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <Tag className="h-3 w-3" aria-hidden />
          <span className="truncate">{paper.domain}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <Clock className="h-3 w-3" aria-hidden />
          <span>{paper.analyzed}</span>
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

function ResearchSnapshot() {
  return (
    <SectionCard eyebrow="This month" title="Research snapshot">
      <ul className="divide-y divide-border">
        {metrics.map((m) => (
          <li key={m.label} className="flex items-baseline justify-between py-3 first:pt-0 last:pb-0">
            <span className="text-sm text-muted-foreground">{m.label}</span>
            <span className="font-serif-editorial text-2xl text-foreground">{m.value}</span>
          </li>
        ))}
      </ul>
    </SectionCard>
  );
}

function ContinueExploring() {
  return (
    <SectionCard eyebrow="Continue exploring" title="Pick up where you left off">
      <div className="flex flex-col gap-5 md:flex-row md:items-center md:justify-between">
        <div className="flex min-w-0 items-start gap-4">
          <div className="grid h-14 w-11 shrink-0 place-items-center rounded-sm border border-border bg-background text-muted-foreground">
            <FileText className="h-4 w-4" aria-hidden />
          </div>
          <div className="min-w-0">
            <h3 className="font-serif-editorial text-lg leading-snug text-foreground">
              {continueReading.title}
            </h3>
            <p className="mt-1 text-xs text-muted-foreground">
              Last viewed section · {continueReading.lastSection}
            </p>
            <div className="mt-3 flex items-center gap-3">
              <div className="h-1 w-48 max-w-full overflow-hidden rounded-full bg-muted">
                <div
                  className="h-full rounded-full bg-primary"
                  style={{ width: `${continueReading.progress}%` }}
                />
              </div>
              <span className="text-xs text-muted-foreground">
                {continueReading.progress}% read
              </span>
            </div>
          </div>
        </div>

        <Link
          to="/paper/$id"
          params={{ id: continueReading.id }}
          className="inline-flex shrink-0 items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition hover:opacity-90"
        >
          Continue reading <ArrowRight className="h-4 w-4" />
        </Link>
      </div>
    </SectionCard>
  );
}
