import { createFileRoute } from "@tanstack/react-router";
import { AppShell } from "@/components/app/AppShell";
import { SectionCard } from "@/components/app/SectionCard";

export const Route = createFileRoute("/settings")({
  head: () => ({
    meta: [
      { title: "Settings · PaperLens" },
      {
        name: "description",
        content: "Manage your PaperLens profile, reading preferences, and notification settings.",
      },
      { property: "og:title", content: "Settings · PaperLens" },
      { property: "og:description", content: "Manage your PaperLens preferences." },
    ],
  }),
  component: SettingsPage,
});

function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block">
      <span className="text-sm font-medium text-foreground">{label}</span>
      {hint && <span className="mt-0.5 block text-xs text-muted-foreground">{hint}</span>}
      <div className="mt-2">{children}</div>
    </label>
  );
}

const inputCls =
  "w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20";

function Toggle({ defaultChecked }: { defaultChecked?: boolean }) {
  return (
    <label className="inline-flex cursor-pointer items-center gap-2">
      <input type="checkbox" defaultChecked={defaultChecked} className="peer sr-only" />
      <span className="relative h-5 w-9 rounded-full bg-muted transition peer-checked:bg-primary">
        <span className="absolute left-0.5 top-0.5 h-4 w-4 rounded-full bg-background transition peer-checked:translate-x-4" />
      </span>
    </label>
  );
}

function SettingsPage() {
  return (
    <AppShell eyebrow="Account" title="Settings">
      <div className="grid gap-6 lg:grid-cols-2">
        <SectionCard eyebrow="Profile" title="Your details">
          <div className="flex items-center gap-4">
            <div className="grid h-14 w-14 place-items-center rounded-full bg-primary text-base font-semibold text-primary-foreground">
              AR
            </div>
            <div>
              <div className="text-sm font-medium text-foreground">Aria Ren</div>
              <div className="text-xs text-muted-foreground">Research fellow · Stanford</div>
            </div>
          </div>
          <div className="mt-6 grid gap-4">
            <Field label="Display name">
              <input className={inputCls} defaultValue="Aria Ren" />
            </Field>
            <Field label="Email">
              <input className={inputCls} defaultValue="aria.ren@example.edu" />
            </Field>
            <Field label="Field of study" hint="Helps tailor summaries to your discipline.">
              <input className={inputCls} defaultValue="Machine Learning · NLP" />
            </Field>
          </div>
        </SectionCard>

        <SectionCard eyebrow="Reading" title="Preferences">
          <div className="space-y-5">
            <div className="flex items-center justify-between gap-4">
              <div>
                <div className="text-sm text-foreground">Editorial serif for paper text</div>
                <div className="text-xs text-muted-foreground">
                  Use Source Serif 4 for abstracts and summaries.
                </div>
              </div>
              <Toggle defaultChecked />
            </div>
            <div className="flex items-center justify-between gap-4">
              <div>
                <div className="text-sm text-foreground">Extract key contributions</div>
                <div className="text-xs text-muted-foreground">
                  Automatically surface main claims after upload.
                </div>
              </div>
              <Toggle defaultChecked />
            </div>
            <div className="flex items-center justify-between gap-4">
              <div>
                <div className="text-sm text-foreground">Email weekly digest</div>
                <div className="text-xs text-muted-foreground">
                  A Monday summary of new papers in your library.
                </div>
              </div>
              <Toggle />
            </div>
          </div>
        </SectionCard>
      </div>

      <div className="mt-6 flex justify-end gap-2">
        <button className="rounded-md border border-border bg-surface px-4 py-2 text-sm text-foreground hover:bg-muted">
          Cancel
        </button>
        <button className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90">
          Save changes
        </button>
      </div>
    </AppShell>
  );
}
