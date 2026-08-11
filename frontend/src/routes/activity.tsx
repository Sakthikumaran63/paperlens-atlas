import { useEffect, useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { AppShell } from "@/components/app/AppShell";
import { SectionCard } from "@/components/app/SectionCard";
import { EmptyState } from "@/components/app/EmptyState";
import { StatusBadge } from "@/components/app/StatusBadge";
import { getPapers, type PaperResponse } from "@/lib/api";
import {
  FileText,
  UploadCloud,
  MessageSquare,
  CheckCircle2,
  Clock,
  Loader2,
  type LucideIcon,
} from "lucide-react";

export const Route = createFileRoute("/activity")({
  head: () => ({
    meta: [
      { title: "Recent Activity · PaperLens" },
      {
        name: "description",
        content:
          "A chronological log of uploads, analyses, and questions across your PaperLens workspace.",
      },
      { property: "og:title", content: "Recent Activity · PaperLens" },
      {
        property: "og:description",
        content: "A chronological log of uploads, analyses, and questions in PaperLens.",
      },
    ],
  }),
  component: ActivityPage,
});

interface ActivityItem {
  id: string;
  kind: "upload" | "analysis" | "question";
  title: string;
  detail: string;
  paperId?: string;
  status?: PaperResponse["status"];
  when: string;
}

const iconFor: Record<ActivityItem["kind"], LucideIcon> = {
  upload: UploadCloud,
  analysis: CheckCircle2,
  question: MessageSquare,
};

function formatTimeAgo(dateStr: string): string {
  if (!dateStr) return "Just now";
  const d = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffMins = Math.floor(diffMs / (1000 * 60));
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins} mins ago`;
  if (diffHours < 24) return `${diffHours} ${diffHours === 1 ? "hour" : "hours"} ago`;
  if (diffDays === 1) return "Yesterday";
  if (diffDays < 7) return `${diffDays} days ago`;
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function ActivityPage() {
  const [papers, setPapers] = useState<PaperResponse[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getPapers()
      .then((data) => setPapers(data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const activities: ActivityItem[] = [];
  papers.forEach((p) => {
    activities.push({
      id: `up-${p.id}`,
      kind: "upload",
      title: "Uploaded research paper",
      detail: `${p.title || p.file_name} • ${p.page_count || 1} pages`,
      paperId: p.id,
      status: p.status,
      when: formatTimeAgo(p.created_at),
    });

    if (p.status === "READY") {
      activities.push({
        id: `an-${p.id}`,
        kind: "analysis",
        title: "Analysis completed",
        detail: `Structure-aware embeddings and 10-field summary ready for ${p.title || p.file_name}`,
        paperId: p.id,
        status: p.status,
        when: formatTimeAgo(p.updated_at || p.created_at),
      });
    }
  });

  return (
    <AppShell eyebrow="Workspace" title="Recent activity">
      <div className="mx-auto max-w-3xl">
        <header className="mb-6">
          <h1 className="font-serif-editorial text-3xl leading-tight text-foreground">
            Recent activity
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            A chronological log of uploads, analyses, and questions in your workspace.
          </p>
        </header>

        {loading ? (
          <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
            <Loader2 className="h-6 w-6 animate-spin mb-2" />
            <p className="text-xs">Loading activity logs...</p>
          </div>
        ) : activities.length === 0 ? (
          <EmptyState
            icon={Clock}
            title="No recent activity"
            description="Upload a research paper PDF to begin logging paper extractions and structure-aware analysis."
          />
        ) : (
          <SectionCard>
            <ol className="relative space-y-5 border-l border-border pl-6">
              {activities.map((e) => {
                const Icon = iconFor[e.kind];
                return (
                  <li key={e.id} className="relative">
                    <span className="absolute -left-[33px] top-0 grid h-6 w-6 place-items-center rounded-full border border-border bg-surface text-muted-foreground">
                      <Icon className="h-3 w-3" aria-hidden />
                    </span>
                    <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
                      <div className="flex items-center gap-2">
                        <div className="text-sm font-medium text-foreground">{e.title}</div>
                        {e.status && <StatusBadge status={e.status} />}
                      </div>
                      <div className="text-[11px] uppercase tracking-wider text-muted-foreground">
                        {e.when}
                      </div>
                    </div>
                    <div className="mt-0.5 text-xs text-muted-foreground">{e.detail}</div>
                    {e.paperId && (
                      <Link
                        to="/paper/$id"
                        params={{ id: e.paperId }}
                        className="mt-1 inline-block text-xs font-medium text-primary hover:underline"
                      >
                        Open paper →
                      </Link>
                    )}
                  </li>
                );
              })}
            </ol>
          </SectionCard>
        )}
      </div>
    </AppShell>
  );
}

