import { createFileRoute, Link } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { UploadCloud, Library } from "lucide-react";
import { AppShell } from "@/components/app/AppShell";
import { PaperCard } from "@/components/app/PaperCard";
import { SearchInput } from "@/components/app/SearchInput";
import { EmptyState } from "@/components/app/EmptyState";
import { mockPapers } from "@/lib/mock-papers";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/papers")({
  head: () => ({
    meta: [
      { title: "My Papers · PaperLens" },
      {
        name: "description",
        content: "Browse, filter, and open the research papers in your PaperLens library.",
      },
      { property: "og:title", content: "My Papers · PaperLens" },
      { property: "og:description", content: "Your PaperLens research library." },
    ],
  }),
  component: PapersPage,
});

const filters = ["All", "Ready", "Processing"] as const;

function PapersPage() {
  const [q, setQ] = useState("");
  const [filter, setFilter] = useState<(typeof filters)[number]>("All");

  const filtered = useMemo(() => {
    return mockPapers.filter((p) => {
      const matchesQ =
        !q ||
        p.title.toLowerCase().includes(q.toLowerCase()) ||
        p.authors.some((a) => a.toLowerCase().includes(q.toLowerCase())) ||
        p.tags.some((t) => t.toLowerCase().includes(q.toLowerCase()));
      const matchesF =
        filter === "All" ||
        (filter === "Ready" && p.status === "ready") ||
        (filter === "Processing" && p.status === "processing");
      return matchesQ && matchesF;
    });
  }, [q, filter]);

  return (
    <AppShell eyebrow="Library" title="My Papers">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="w-full sm:max-w-sm">
          <SearchInput
            placeholder="Search by title, author, or tag"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
        </div>
        <div className="flex items-center gap-1 rounded-md border border-border bg-surface p-1">
          {filters.map((f) => (
            <button
              key={f}
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
      </div>

      <div className="mt-6">
        {filtered.length === 0 ? (
          <EmptyState
            icon={Library}
            title="No papers match your filters"
            description="Try a different search term, or upload a new paper to your library."
            action={
              <Link
                to="/upload"
                className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground"
              >
                <UploadCloud className="h-4 w-4" /> Upload paper
              </Link>
            }
          />
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {filtered.map((p) => (
              <PaperCard key={p.id} paper={p} />
            ))}
          </div>
        )}
      </div>
    </AppShell>
  );
}
