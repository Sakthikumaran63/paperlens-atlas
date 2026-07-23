import { createFileRoute, Link } from "@tanstack/react-router";
import { Library, MessagesSquare, Sparkles, UploadCloud, ArrowRight } from "lucide-react";
import { AppShell } from "@/components/app/AppShell";
import { MetricCard } from "@/components/app/MetricCard";
import { SectionCard } from "@/components/app/SectionCard";
import { PaperCard } from "@/components/app/PaperCard";
import { mockPapers, recentActivity } from "@/lib/mock-papers";

export const Route = createFileRoute("/dashboard")({
  head: () => ({
    meta: [
      { title: "Overview · PaperLens" },
      {
        name: "description",
        content:
          "Your research workspace overview: library size, recent activity, and quick actions in PaperLens.",
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

function DashboardPage() {
  const recent = mockPapers.slice(0, 3);

  return (
    <AppShell eyebrow="Workspace" title="Overview">
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <MetricCard label="Papers in library" value={mockPapers.length} icon={Library} delta="+2 this week" />
        <MetricCard label="Questions asked" value={48} icon={MessagesSquare} delta="12 today" />
        <MetricCard label="Summaries generated" value={17} icon={Sparkles} delta="+4 this week" />
        <MetricCard label="Uploads pending" value={1} icon={UploadCloud} />
      </div>

      <div className="mt-8 grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <SectionCard
            eyebrow="Continue reading"
            title="Recently added papers"
            action={
              <Link
                to="/papers"
                className="inline-flex items-center gap-1 text-sm text-primary hover:underline"
              >
                All papers <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            }
          >
            <div className="grid gap-4 sm:grid-cols-2">
              {recent.map((p) => (
                <PaperCard key={p.id} paper={p} />
              ))}
            </div>
          </SectionCard>
        </div>

        <div className="space-y-6">
          <SectionCard eyebrow="Activity" title="Recent activity">
            <ol className="space-y-4">
              {recentActivity.map((a) => (
                <li key={a.id} className="flex gap-3">
                  <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
                  <div className="min-w-0">
                    <p className="text-sm text-foreground">{a.title}</p>
                    <p className="text-xs text-muted-foreground">{a.when}</p>
                  </div>
                </li>
              ))}
            </ol>
          </SectionCard>

          <SectionCard eyebrow="Get started" title="Add your next paper">
            <p className="text-sm text-muted-foreground">
              Upload a PDF to extract its abstract, methodology, and key contributions in seconds.
            </p>
            <Link
              to="/upload"
              className="mt-4 inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition hover:opacity-90"
            >
              <UploadCloud className="h-4 w-4" /> Upload paper
            </Link>
          </SectionCard>
        </div>
      </div>
    </AppShell>
  );
}
