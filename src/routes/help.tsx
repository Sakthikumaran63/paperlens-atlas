import { createFileRoute, Link } from "@tanstack/react-router";
import { AppShell } from "@/components/app/AppShell";
import { SectionCard } from "@/components/app/SectionCard";
import { BookOpen, MessageSquare, Keyboard, LifeBuoy } from "lucide-react";

export const Route = createFileRoute("/help")({
  head: () => ({
    meta: [
      { title: "Help · PaperLens" },
      {
        name: "description",
        content:
          "Documentation, shortcuts, and support for getting the most out of PaperLens.",
      },
      { property: "og:title", content: "Help · PaperLens" },
      {
        property: "og:description",
        content: "Documentation, shortcuts, and support for PaperLens.",
      },
    ],
  }),
  component: HelpPage,
});

const faqs = [
  {
    q: "What file types can I upload?",
    a: "PaperLens accepts research papers as PDF files up to 20 MB. English-language papers work best.",
  },
  {
    q: "How are answers grounded?",
    a: "Every answer cites the source page and section. Open a paper and use the assistant panel to see citations inline.",
  },
  {
    q: "Where is my data stored?",
    a: "Papers stay in your workspace. In this prototype no files leave the browser session.",
  },
  {
    q: "Can I export my workspace?",
    a: "Yes — go to Settings › Data › Export workspace to download a copy.",
  },
];

const shortcuts = [
  { keys: "⌘K", label: "Open search" },
  { keys: "G then P", label: "Go to My Papers" },
  { keys: "U", label: "Upload a paper" },
  { keys: "?", label: "Show keyboard shortcuts" },
];

function HelpPage() {
  return (
    <AppShell eyebrow="Support" title="Help">
      <div className="mx-auto max-w-3xl space-y-6">
        <header>
          <h1 className="font-serif-editorial text-3xl leading-tight text-foreground">
            Help &amp; documentation
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Guides and shortcuts for getting the most out of PaperLens.
          </p>
        </header>

        <div className="grid gap-4 sm:grid-cols-3">
          {[
            { icon: BookOpen, title: "Getting started", desc: "Upload, analyze, and read your first paper." },
            { icon: Keyboard, title: "Shortcuts", desc: "Navigate PaperLens without leaving the keyboard." },
            { icon: MessageSquare, title: "Contact us", desc: "Reach the team for questions or feedback." },
          ].map((c) => (
            <div
              key={c.title}
              className="rounded-lg border border-border bg-surface p-5 transition hover:border-primary/50"
            >
              <c.icon className="h-4 w-4 text-primary" aria-hidden />
              <div className="mt-3 text-sm font-medium text-foreground">{c.title}</div>
              <div className="mt-1 text-xs text-muted-foreground">{c.desc}</div>
            </div>
          ))}
        </div>

        <SectionCard eyebrow="Reference" title="Keyboard shortcuts">
          <ul className="divide-y divide-border">
            {shortcuts.map((s) => (
              <li key={s.label} className="flex items-center justify-between py-3 text-sm">
                <span className="text-foreground">{s.label}</span>
                <kbd className="rounded border border-border bg-background px-2 py-0.5 font-sans text-[11px] text-muted-foreground">
                  {s.keys}
                </kbd>
              </li>
            ))}
          </ul>
        </SectionCard>

        <SectionCard eyebrow="FAQ" title="Frequently asked">
          <div className="divide-y divide-border">
            {faqs.map((f) => (
              <div key={f.q} className="py-4 first:pt-0 last:pb-0">
                <div className="font-serif-editorial text-base text-foreground">{f.q}</div>
                <p className="mt-1 text-sm text-muted-foreground">{f.a}</p>
              </div>
            ))}
          </div>
        </SectionCard>

        <div className="flex flex-col items-start gap-3 rounded-lg border border-border bg-surface p-5 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <span className="grid h-9 w-9 place-items-center rounded-md bg-accent text-primary">
              <LifeBuoy className="h-4 w-4" />
            </span>
            <div>
              <div className="text-sm font-medium text-foreground">Still stuck?</div>
              <div className="text-xs text-muted-foreground">
                We usually reply within a business day.
              </div>
            </div>
          </div>
          <Link
            to="/settings"
            className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition hover:bg-primary/90"
          >
            Contact support
          </Link>
        </div>
      </div>
    </AppShell>
  );
}
