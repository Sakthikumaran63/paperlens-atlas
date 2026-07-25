import { createFileRoute, Link, notFound } from "@tanstack/react-router";
import { useState } from "react";
import { ArrowLeft, BookOpen, Send, Sparkles, Users, Calendar, FileText } from "lucide-react";
import { AppShell } from "@/components/app/AppShell";
import { SectionCard } from "@/components/app/SectionCard";
import { StatusBadge } from "@/components/app/StatusBadge";
import { PdfReader } from "@/components/app/PdfReader";
import { getPaper, type Paper } from "@/lib/mock-papers";

export const Route = createFileRoute("/paper/$id")({
  loader: ({ params }) => {
    const paper = getPaper(params.id);
    if (!paper) throw notFound();
    return { paper };
  },
  head: ({ loaderData }) => {
    const title = loaderData?.paper.title ?? "Paper";
    return {
      meta: [
        { title: `${title} · PaperLens` },
        {
          name: "description",
          content: loaderData?.paper.abstract.slice(0, 155) ?? "Read this paper in PaperLens.",
        },
        { property: "og:title", content: `${title} · PaperLens` },
        {
          property: "og:description",
          content: loaderData?.paper.abstract.slice(0, 155) ?? "Read this paper in PaperLens.",
        },
      ],
    };
  },
  component: PaperDetailPage,
});

interface Msg {
  role: "user" | "assistant";
  text: string;
}

function PaperDetailPage() {
  const { paper } = Route.useLoaderData() as { paper: Paper };
  const [readerOpen, setReaderOpen] = useState(false);
  const [messages, setMessages] = useState<Msg[]>([
    {
      role: "assistant",
      text: `Hi! I've read "${paper.title}". Ask me about its methodology, results, or contributions.`,
    },
  ]);
  const [input, setInput] = useState("");

  const send = (e: React.FormEvent) => {
    e.preventDefault();
    const value = input.trim();
    if (!value) return;
    setMessages((m) => [...m, { role: "user", text: value }]);
    setInput("");
    setTimeout(() => {
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          text: `Based on the paper, ${paper.keyContributions[0].toLowerCase()} This is a mocked answer while the reasoning backend is being connected.`,
        },
      ]);
    }, 550);
  };

  return (
    <AppShell eyebrow={`${paper.venue} · ${paper.year}`} title="Paper reader">
      {readerOpen && <PdfReader paper={paper} onClose={() => setReaderOpen(false)} />}
      <div className="flex items-center justify-between gap-3">
        <Link
          to="/papers"
          className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-3.5 w-3.5" /> Back to library
        </Link>
        <button
          onClick={() => setReaderOpen(true)}
          className="inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:opacity-90"
        >
          <BookOpen className="h-3.5 w-3.5" /> Open PDF
        </button>
      </div>

      <div className="mt-4 grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <SectionCard>
            <div className="flex items-start justify-between gap-4">
              <div className="flex items-start gap-4">
                <div className="grid h-14 w-11 shrink-0 place-items-center rounded-sm border border-border bg-background text-muted-foreground">
                  <FileText className="h-4 w-4" aria-hidden />
                </div>
                <div>
                  <div className="flex flex-wrap gap-2">
                    {paper.tags.map((t) => (
                      <span
                        key={t}
                        className="rounded-full border border-border px-2 py-0.5 text-[11px] text-muted-foreground"
                      >
                        {t}
                      </span>
                    ))}
                  </div>
                  <h2 className="mt-3 font-serif-editorial text-2xl leading-tight text-foreground md:text-3xl">
                    {paper.title}
                  </h2>
                  <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted-foreground">
                    <span className="inline-flex items-center gap-1.5">
                      <Users className="h-3.5 w-3.5" /> {paper.authors.join(", ")}
                    </span>
                    <span className="inline-flex items-center gap-1.5">
                      <Calendar className="h-3.5 w-3.5" /> {paper.venue} · {paper.year}
                    </span>
                    <span>{paper.pages} pages</span>
                    <span>{paper.citations.toLocaleString()} citations</span>
                  </div>
                </div>
              </div>
              <StatusBadge status={paper.status} />
            </div>
          </SectionCard>

          <SectionCard eyebrow="Abstract" title="Summary">
            <p className="font-serif-editorial text-[15px] leading-relaxed text-foreground/90">
              {paper.abstract}
            </p>
          </SectionCard>

          <div className="grid gap-6 md:grid-cols-2">
            <SectionCard eyebrow="Contributions" title="Key contributions">
              <ul className="space-y-3">
                {paper.keyContributions.map((c, i) => (
                  <li key={i} className="flex gap-3 text-sm text-foreground/90">
                    <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
                    <span>{c}</span>
                  </li>
                ))}
              </ul>
            </SectionCard>

            <SectionCard eyebrow="Approach" title="Methodology">
              <ul className="space-y-3">
                {paper.methodology.map((c, i) => (
                  <li key={i} className="flex gap-3 text-sm text-foreground/90">
                    <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-foreground/40" />
                    <span>{c}</span>
                  </li>
                ))}
              </ul>
            </SectionCard>
          </div>

          <SectionCard eyebrow="Findings" title="Results">
            <ul className="space-y-3">
              {paper.results.map((c, i) => (
                <li key={i} className="flex gap-3 text-sm text-foreground/90">
                  <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-[color:var(--sage)]" />
                  <span>{c}</span>
                </li>
              ))}
            </ul>
          </SectionCard>
        </div>

        <div className="lg:sticky lg:top-20 lg:h-[calc(100vh-6rem)]">
          <SectionCard
            eyebrow="Ask the paper"
            title="Grounded Q&A"
            className="flex h-full flex-col"
          >
            <div className="mb-3 inline-flex w-fit items-center gap-1.5 rounded-full border border-border bg-background px-2 py-0.5 text-[11px] text-muted-foreground">
              <Sparkles className="h-3 w-3 text-primary" /> Mock responses
            </div>
            <div className="flex-1 space-y-3 overflow-y-auto pr-1">
              {messages.map((m, i) => (
                <div
                  key={i}
                  className={
                    m.role === "assistant"
                      ? "rounded-md border border-border bg-background p-3 text-sm text-foreground"
                      : "rounded-md bg-accent p-3 text-sm text-accent-foreground"
                  }
                >
                  {m.text}
                </div>
              ))}
            </div>
            <form onSubmit={send} className="mt-4 flex items-center gap-2">
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask about methodology, results…"
                className="flex-1 rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
              />
              <button
                type="submit"
                aria-label="Send question"
                className="grid h-9 w-9 place-items-center rounded-md bg-primary text-primary-foreground transition hover:opacity-90"
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
