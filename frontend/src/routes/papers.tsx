import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useMemo, useState } from "react";
import {
  UploadCloud,
  FileText,
  MoreHorizontal,
  Pencil,
  Trash2,
  RotateCw,
  AlertTriangle,
} from "lucide-react";
import { toast } from "sonner";
import { AppShell } from "@/components/app/AppShell";
import { SearchInput } from "@/components/app/SearchInput";
import { EmptyState } from "@/components/app/EmptyState";
import { StatusBadge } from "@/components/app/StatusBadge";
import { deletePaper, getPapers, retryPaperPipeline, type PaperResponse } from "@/lib/api";
import { cn } from "@/lib/utils";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { ConfirmDialog } from "@/components/app/states/ConfirmDialog";
import { ErrorState } from "@/components/app/states/StatePanels";

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
  { id: "recent-added", label: "Recently added" },
  { id: "title-asc", label: "Title A–Z" },
] as const;
type SortId = (typeof SORTS)[number]["id"];

function matchesFilter(status: string, filter: Filter) {
  if (filter === "All") return true;
  return status.toUpperCase() === filter.toUpperCase();
}

function formatDate(iso: string) {
  if (!iso) return "Recent";
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

function PapersPage() {
  const [papers, setPapers] = useState<PaperResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [q, setQ] = useState("");
  const [filter, setFilter] = useState<Filter>("All");
  const [sort, setSort] = useState<SortId>("recent-added");
  const [pendingDelete, setPendingDelete] = useState<PaperResponse | null>(null);

  const fetchPapersList = async () => {
    setLoading(true);
    setErrorMessage(null);
    try {
      const list = await getPapers();
      setPapers(list);
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to load papers library.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPapersList();
  }, []);

  const filtered = useMemo(() => {
    const query = q.trim().toLowerCase();
    const list = papers.filter((p) => {
      const matchesQ =
        !query ||
        p.title.toLowerCase().includes(query) ||
        (p.authors && p.authors.toLowerCase().includes(query)) ||
        p.file_name.toLowerCase().includes(query);
      return matchesQ && matchesFilter(p.status, filter);
    });

    const sorted = [...list];
    if (sort === "title-asc") {
      sorted.sort((a, b) => a.title.localeCompare(b.title));
    } else {
      sorted.sort((a, b) => (a.created_at < b.created_at ? 1 : -1));
    }
    return sorted;
  }, [papers, q, filter, sort]);

  const isLibraryEmpty = papers.length === 0 && !loading && !errorMessage;

  const handleRename = (paper: PaperResponse) => {
    const next = window.prompt("Rename paper", paper.title);
    if (!next || next.trim() === "" || next === paper.title) return;
    setPapers((prev) => prev.map((p) => (p.id === paper.id ? { ...p, title: next.trim() } : p)));
    toast.success("Paper renamed successfully");
  };

  const confirmDelete = async () => {
    if (!pendingDelete) return;
    const id = pendingDelete.id;
    try {
      await deletePaper(id);
      setPapers((prev) => prev.filter((p) => p.id !== id));
      toast.success("Paper deleted successfully");
    } catch (err: any) {
      toast.error(err.message || "Failed to delete paper.");
    } finally {
      setPendingDelete(null);
    }
  };

  const handleRetry = async (paperId: string) => {
    try {
      await retryPaperPipeline(paperId);
      toast.success("Pipeline retry triggered in background.");
      fetchPapersList();
    } catch (err: any) {
      toast.error(err.message || "Failed to trigger retry.");
    }
  };

  return (
    <AppShell eyebrow="Library" title="My Papers">
      {/* Page header */}
      <header className="flex flex-col gap-4 border-b border-border/60 pb-6 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="font-serif-editorial text-3xl leading-tight text-foreground">My Papers</h1>
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
          {/* Status filter tabs */}
          <div className="flex rounded-md border border-border bg-background p-0.5 text-xs">
            {FILTERS.map((f) => (
              <button
                key={f}
                type="button"
                onClick={() => setFilter(f)}
                className={cn(
                  "rounded-sm px-3 py-1.5 font-medium transition",
                  filter === f
                    ? "bg-accent text-accent-foreground shadow-xs"
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                {f}
              </button>
            ))}
          </div>

          {/* Sort select */}
          <select
            value={sort}
            onChange={(e) => setSort(e.target.value as SortId)}
            className="rounded-md border border-border bg-background px-3 py-1.5 text-xs text-foreground focus:border-primary focus:outline-none"
          >
            {SORTS.map((s) => (
              <option key={s.id} value={s.id}>
                {s.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Main Content Area */}
      {loading ? (
        <div className="mt-8 py-16 text-center text-sm text-muted-foreground">
          Loading paper library...
        </div>
      ) : errorMessage ? (
        <div className="mt-8">
          <ErrorState
            title="Failed to load library"
            description={errorMessage}
            onRetry={fetchPapersList}
          />
        </div>
      ) : isLibraryEmpty ? (
        <div className="mt-8">
          <EmptyState
            title="No papers in library yet"
            description="Upload your first research paper PDF to structure sections and enable grounded Q&A."
            actionLabel="Upload First Paper"
            onAction={() => (window.location.href = "/upload")}
          />
        </div>
      ) : filtered.length === 0 ? (
        <div className="mt-8 py-12 text-center text-sm text-muted-foreground">
          No papers match your search criteria. Try adjusting filters or query.
        </div>
      ) : (
        <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((paper) => {
            const mappedStatus = paper.status.toLowerCase() as "ready" | "processing" | "failed";
            return (
              <div
                key={paper.id}
                className="group relative flex flex-col justify-between rounded-lg border border-border bg-surface p-5 transition hover:border-border/80 hover:shadow-xs"
              >
                <div>
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-2">
                      <div className="grid h-9 w-9 shrink-0 place-items-center rounded-md border border-border bg-background text-muted-foreground">
                        <FileText className="h-4 w-4" aria-hidden />
                      </div>
                      <div>
                        <span className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                          {formatDate(paper.created_at)}
                        </span>
                        <div className="text-xs text-muted-foreground">
                          {paper.page_count} pages
                        </div>
                      </div>
                    </div>
                    <StatusBadge status={mappedStatus} />
                  </div>

                  <h3 className="mt-3 font-serif-editorial text-lg leading-snug text-foreground group-hover:text-primary">
                    <Link to="/paper/$id" params={{ id: paper.id }}>
                      {paper.title}
                    </Link>
                  </h3>

                  {paper.authors && (
                    <p className="mt-1 line-clamp-1 text-xs text-muted-foreground">
                      {paper.authors}
                    </p>
                  )}
                </div>

                <div className="mt-5 flex items-center justify-between border-t border-border/40 pt-3 text-xs text-muted-foreground">
                  <div className="flex items-center gap-2">
                    {paper.status === "FAILED" && (
                      <button
                        type="button"
                        onClick={() => handleRetry(paper.id)}
                        className="inline-flex items-center gap-1 text-destructive hover:underline"
                      >
                        <RotateCw className="h-3 w-3" /> Retry
                      </button>
                    )}
                    {paper.status === "PROCESSING" && (
                      <span className="text-xs text-[color:var(--ochre)] font-medium">
                        {paper.progress}% {paper.stage}
                      </span>
                    )}
                  </div>

                  <DropdownMenu>
                    <DropdownMenuTrigger className="rounded-md p-1 hover:bg-muted focus:outline-none">
                      <MoreHorizontal className="h-4 w-4" />
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem onClick={() => handleRename(paper)}>
                        <Pencil className="mr-2 h-3.5 w-3.5" /> Rename
                      </DropdownMenuItem>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem
                        onClick={() => setPendingDelete(paper)}
                        className="text-destructive focus:text-destructive"
                      >
                        <Trash2 className="mr-2 h-3.5 w-3.5" /> Delete
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        open={Boolean(pendingDelete)}
        onOpenChange={(open) => !open && setPendingDelete(null)}
        title="Delete paper?"
        description={`Are you sure you want to delete "${pendingDelete?.title}"? All extracted sections and embeddings will be permanently removed.`}
        confirmLabel="Delete Paper"
        tone="danger"
        onConfirm={confirmDelete}
      />
    </AppShell>
  );
}
