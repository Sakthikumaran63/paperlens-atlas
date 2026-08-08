import { createFileRoute, Link } from "@tanstack/react-router";
import { AppShell } from "@/components/app/AppShell";
import { SectionCard } from "@/components/app/SectionCard";
import { EmptyState } from "@/components/app/EmptyState";
import {
  FileText,
  UploadCloud,
  MessageSquare,
  CheckCircle2,
  Clock,
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

interface Entry {
  id: string;
  kind: "upload" | "analysis" | "question" | "note";
  title: string;
  detail: string;
  paperId?: string;
  when: string;
}

const iconFor: Record<Entry["kind"], LucideIcon> = {
  upload: UploadCloud,
  analysis: CheckCircle2,
  question: MessageSquare,
  note: FileText,
};

const entries: Entry[] = [
  {
    id: "1",
    kind: "question",
    title: "Asked about scaled dot-product attention",
    detail: "Attention Is All You Need · §3.2",
    paperId: "attention-is-all-you-need",
    when: "2 hours ago",
  },
  {
    id: "2",
    kind: "analysis",
    title: "Analysis completed",
    detail: "BERT: Pre-training of Deep Bidirectional Transformers",
    paperId: "bert",
    when: "Yesterday, 4:12 PM",
  },
  {
    id: "3",
    kind: "upload",
    title: "Uploaded paper",
    detail: "Deep Residual Learning for Image Recognition · 12 pages",
    paperId: "resnet",
    when: "Yesterday, 4:08 PM",
  },
  {
    id: "4",
    kind: "note",
    title: "Saved 3 highlights",
    detail: "Attention Is All You Need · §5 Results",
    paperId: "attention-is-all-you-need",
    when: "3 days ago",
  },
  {
    id: "5",
    kind: "question",
    title: "Asked about training data",
    detail: "GPT-3 · §2.2",
    when: "Last week",
  },
];

function ActivityPage() {
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

        {entries.length === 0 ? (
          <EmptyState
            icon={Clock}
            title="No activity yet"
            description="Uploads, analyses, and questions will appear here."
          />
        ) : (
          <SectionCard>
            <ol className="relative space-y-5 border-l border-border pl-6">
              {entries.map((e) => {
                const Icon = iconFor[e.kind];
                return (
                  <li key={e.id} className="relative">
                    <span className="absolute -left-[33px] top-0 grid h-6 w-6 place-items-center rounded-full border border-border bg-surface text-muted-foreground">
                      <Icon className="h-3 w-3" aria-hidden />
                    </span>
                    <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
                      <div className="text-sm font-medium text-foreground">{e.title}</div>
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
