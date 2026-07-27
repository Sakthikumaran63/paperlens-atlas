import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import {
  UploadCloud,
  Library,
  FileText,
  MoreHorizontal,
  ArrowUpRight,
  Pencil,
  Trash2,
  FolderOpen,
} from "lucide-react";
import { toast } from "sonner";
import { AppShell } from "@/components/app/AppShell";
import { SearchInput } from "@/components/app/SearchInput";
import { EmptyState } from "@/components/app/EmptyState";
import { StatusBadge } from "@/components/app/StatusBadge";
import { mockPapers, type Paper, type PaperStatus } from "@/lib/mock-papers";
import { cn } from "@/lib/utils";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { ConfirmDialog } from "@/components/app/states/ConfirmDialog";
import { Search as SearchIcon } from "lucide-react";

export const Route = createFileRoute("/papers")({
  head: () => ({
    meta: [
      { title: "My Papers · PaperLens" },
      {
        name: "description",
        content: "Your analyzed research papers in one place — search, filter, and open them.",
      },
      { property: "og:title", content: "My Papers · PaperLens" },
      {
        property: "og:description",
        content: "Your analyzed research papers in one place.",
      },
    ],
  }),
  component: PapersPage,
});

const FILTERS = ["All", "Ready", "Processing", "Failed"] as const;
type Filter = (typeof FILTERS)[number];

const SORTS = [
  { id: "recent-analyzed", label: "Recently analyzed" },
  { id: "recent-added", label: "Recently added" },
  { id: "title-asc", label: "Title A–Z" },
] as const;
type SortId = (typeof SORTS)[number]["id"];

function matchesFilter(status: PaperStatus, filter: Filter) {
  if (filter === "All") return true;
  return status === (filter.toLowerCase() as PaperStatus);
}

function formatDate(iso: string) {
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

function PapersPage() {
  const [papers, setPapers] = useState<Paper[]>(mockPapers);
  const [q, setQ] = useState("");
  const [filter, setFilter] = useState<Filter>("All");
  const [sort, setSort] = useState<SortId>("recent-analyzed");

  const filtered = useMemo(() => {
    const query = q.trim().toLowerCase();
    const list = papers.filter((p) => {
      const matchesQ =
        !query ||
        p.title.toLowerCase().includes(query) ||
        p.authors.some((a) => a.toLowerCase().includes(query)) ||
        p.tags.some((t) => t.toLowerCase().includes(query)) ||
        p.venue.toLowerCase().includes(query);
      return matchesQ && matchesFilter(p.status, filter);
    });

    const sorted = [...list];
    if (sort === "title-asc") {
      sorted.sort((a, b) => a.title.localeCompare(b.title));
    } else {
      // Both date sorts use addedAt in mock data; treat "recently analyzed" the same.
      sorted.sort((a, b) => (a.addedAt < b.addedAt ? 1 : -1));
    }
    return sorted;
  }, [papers, q, filter, sort]);

  const isLibraryEmpty = papers.length === 0;

  function handleRename(paper: Paper) {
    const next = window.prompt("Rename paper", paper.title);
    if (!next || next.trim() === "" || next === paper.title) return;
    setPapers((prev) =>
      prev.map((p) => (p.id === paper.id ? { ...p, title: next.trim() } : p)),
    );
    toast.success("Paper renamed");
  }

  function handleDelete(paper: Paper) {
    if (!window.confirm(`Delete "${paper.title}" from your library?`)) return;
    setPapers((prev) => prev.filter((p) => p.id !== paper.id));
    toast.success("Paper removed from library");
  }

  return (
    <AppShell eyebrow="Library" title="My Papers">
      {/* Page header */}
      <header className="flex flex-col gap-4 border-b border-border/60 pb-6 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="font-serif-editorial text-3xl leading-tight text-foreground">
            My Papers
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Your analyzed research papers in one place.
          </p>
        </div>
        <Link
          to="/upload"
          className="inline-flex items-center gap-2 self-start rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition hover:bg-primary/90 sm:self-auto"
        >
          <UploadCloud className="h-4 w-4" />
          Upload Paper
        </Link>
      </header>

      {/* Controls */}
      <div className="mt-6 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="w-full lg:max-w-sm">
          <SearchInput
            placeholder="Search papers..."
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <div
            role="tablist"
            aria-label="Filter by status"
            className="flex items-center gap-1 rounded-md border border-border bg-surface p-1"
          >
            {FILTERS.map((f) => (
              <button
                key={f}
                role="tab"
                aria-selected={filter === f}
                type="button"
                onClick={() => setFilter(f)}
                className={cn(
                  "rounded px-3 py-1.5 text-sm transition",
                  filter === f
                    ? "bg-accent text-primary"
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                {f}
              </button>
            ))}
          </div>

          <label className="flex items-center gap-2 text-sm text-muted-foreground">
            <span className="hidden sm:inline">Sort</span>
            <select
              value={sort}
              onChange={(e) => setSort(e.target.value as SortId)}
              className="rounded-md border border-border bg-surface px-3 py-1.5 text-sm text-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30"
            >
              {SORTS.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.label}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>

      {/* Grid / empty state */}
      <section className="mt-8">
        {isLibraryEmpty ? (
          <EmptyState
            icon={Library}
            title="Your research library is empty"
            description="Upload your first paper to begin analyzing it."
            action={
              <Link
                to="/upload"
                className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground"
              >
                <UploadCloud className="h-4 w-4" /> Upload PDF
              </Link>
            }
          />
        ) : filtered.length === 0 ? (
          <EmptyState
            icon={FolderOpen}
            title="No papers match your filters"
            description="Try a different search term or clear the current filter."
            action={
              <button
                type="button"
                onClick={() => {
                  setQ("");
                  setFilter("All");
                }}
                className="inline-flex items-center gap-2 rounded-md border border-border bg-surface px-4 py-2 text-sm text-foreground hover:border-primary/60"
              >
                Reset filters
              </button>
            }
          />
        ) : (
          <ul className="grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-3">
            {filtered.map((p) => (
              <li key={p.id}>
                <LibraryPaperCard
                  paper={p}
                  onRename={() => handleRename(p)}
                  onDelete={() => handleDelete(p)}
                />
              </li>
            ))}
          </ul>
        )}
      </section>
    </AppShell>
  );
}

interface CardProps {
  paper: Paper;
  onRename: () => void;
  onDelete: () => void;
}

function LibraryPaperCard({ paper, onRename, onDelete }: CardProps) {
  const navigate = useNavigate();
  const domain = paper.tags[0] ?? paper.venue;
  const open = () => navigate({ to: "/paper/$id", params: { id: paper.id } });

  return (
    <article className="group flex h-full flex-col rounded-lg border border-border bg-surface p-5 transition hover:border-primary/50">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="flex h-9 w-7 items-center justify-center rounded-sm border border-border bg-background text-muted-foreground">
            <FileText className="h-3.5 w-3.5" aria-hidden />
          </span>
          <span className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
            PDF
          </span>
        </div>

        <div className="flex items-center gap-2">
          <StatusBadge status={paper.status} />
          <DropdownMenu>
            <DropdownMenuTrigger
              aria-label="Paper actions"
              className="grid h-8 w-8 place-items-center rounded-md text-muted-foreground transition hover:bg-background hover:text-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30"
            >
              <MoreHorizontal className="h-4 w-4" />
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-40">
              <DropdownMenuItem onSelect={open}>
                <ArrowUpRight className="mr-2 h-4 w-4" /> Open
              </DropdownMenuItem>
              <DropdownMenuItem onSelect={onRename}>
                <Pencil className="mr-2 h-4 w-4" /> Rename
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                onSelect={onDelete}
                className="text-destructive focus:text-destructive"
              >
                <Trash2 className="mr-2 h-4 w-4" /> Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      <h3 className="mt-4 font-serif-editorial text-lg leading-snug text-foreground">
        {paper.title}
      </h3>

      <p className="mt-2 text-xs text-muted-foreground">
        <span className="truncate">
          {paper.authors.slice(0, 2).join(", ")}
          {paper.authors.length > 2 && ` +${paper.authors.length - 2}`}
        </span>
        <span className="mx-1.5 opacity-50">·</span>
        <span>{paper.year}</span>
      </p>

      <div className="mt-3 flex flex-wrap items-center gap-1.5">
        <span className="rounded-full border border-border bg-background px-2 py-0.5 text-[11px] text-muted-foreground">
          {domain}
        </span>
      </div>

      <dl className="mt-4 space-y-1 text-xs text-muted-foreground">
        <div className="flex justify-between">
          <dt>Uploaded</dt>
          <dd className="text-foreground/80">{formatDate(paper.addedAt)}</dd>
        </div>
        <div className="flex justify-between">
          <dt>Analysis</dt>
          <dd className="capitalize text-foreground/80">{paper.status}</dd>
        </div>
      </dl>

      <div className="mt-5 flex items-center justify-between border-t border-border/60 pt-4">
        <button
          type="button"
          onClick={open}
          className="inline-flex items-center gap-1.5 text-sm font-medium text-primary transition hover:opacity-80"
        >
          Open <ArrowUpRight className="h-3.5 w-3.5" />
        </button>
        <span className="text-[11px] text-muted-foreground">{paper.pages} pages</span>
      </div>
    </article>
  );
}
