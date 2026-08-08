import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { AppShell } from "@/components/app/AppShell";
import { SectionCard } from "@/components/app/SectionCard";
import { Sun, Moon, Download, Trash2, Camera } from "lucide-react";

export const Route = createFileRoute("/settings")({
  head: () => ({
    meta: [
      { title: "Settings · PaperLens" },
      {
        name: "description",
        content: "Manage your PaperLens profile, workspace, appearance, and reading preferences.",
      },
      { property: "og:title", content: "Settings · PaperLens" },
      {
        property: "og:description",
        content: "Manage your PaperLens profile, workspace, and preferences.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
    ],
  }),
  component: SettingsPage,
});

const inputCls =
  "w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20";

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

function Toggle({ checked, onChange }: { checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className={`relative h-5 w-9 rounded-full transition ${checked ? "bg-primary" : "bg-muted"}`}
    >
      <span
        className={`absolute top-0.5 h-4 w-4 rounded-full bg-background transition ${
          checked ? "left-[1.125rem]" : "left-0.5"
        }`}
      />
    </button>
  );
}

function ToggleRow({
  title,
  description,
  checked,
  onChange,
}: {
  title: string;
  description: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <div className="flex items-center justify-between gap-4 py-3">
      <div className="min-w-0">
        <div className="text-sm text-foreground">{title}</div>
        <div className="mt-0.5 text-xs text-muted-foreground">{description}</div>
      </div>
      <Toggle checked={checked} onChange={onChange} />
    </div>
  );
}

function SettingsPage() {
  const [theme, setTheme] = useState<"light" | "dark">("light");
  const [defaultView, setDefaultView] = useState("grid");
  const [autoOpen, setAutoOpen] = useState(true);
  const [showSources, setShowSources] = useState(true);
  const [chatHistory, setChatHistory] = useState(true);

  return (
    <AppShell eyebrow="Account" title="Settings">
      <div className="mx-auto max-w-3xl space-y-6">
        {/* Profile */}
        <SectionCard eyebrow="Profile" title="Your details">
          <div className="flex items-center gap-4">
            <div className="relative">
              <div className="grid h-16 w-16 place-items-center rounded-full bg-primary text-lg font-semibold text-primary-foreground">
                AR
              </div>
              <button
                type="button"
                className="absolute -bottom-1 -right-1 grid h-6 w-6 place-items-center rounded-full border border-border bg-surface text-foreground hover:bg-muted"
                aria-label="Change avatar"
              >
                <Camera className="h-3 w-3" />
              </button>
            </div>
            <div className="min-w-0">
              <div className="text-sm font-medium text-foreground">Profile avatar</div>
              <div className="text-xs text-muted-foreground">PNG or JPG, up to 2 MB.</div>
            </div>
          </div>
          <div className="mt-6 grid gap-4 sm:grid-cols-2">
            <Field label="Name">
              <input className={inputCls} defaultValue="Aria Ren" />
            </Field>
            <Field label="Email">
              <input type="email" className={inputCls} defaultValue="aria.ren@example.edu" />
            </Field>
          </div>
        </SectionCard>

        {/* Workspace */}
        <SectionCard eyebrow="Workspace" title="Workspace settings">
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Workspace name">
              <input className={inputCls} defaultValue="Aria's Research" />
            </Field>
            <Field label="Default paper view" hint="How papers appear in your library.">
              <select
                className={inputCls}
                value={defaultView}
                onChange={(e) => setDefaultView(e.target.value)}
              >
                <option value="grid">Grid</option>
                <option value="list">List</option>
                <option value="compact">Compact</option>
              </select>
            </Field>
          </div>
        </SectionCard>

        {/* Appearance */}
        <SectionCard eyebrow="Appearance" title="Theme">
          <div className="grid gap-3 sm:grid-cols-2">
            {(["light", "dark"] as const).map((mode) => {
              const active = theme === mode;
              const Icon = mode === "light" ? Sun : Moon;
              return (
                <button
                  key={mode}
                  type="button"
                  onClick={() => setTheme(mode)}
                  className={`flex items-center gap-3 rounded-md border px-4 py-3 text-left transition ${
                    active
                      ? "border-primary bg-primary/5"
                      : "border-border bg-background hover:bg-muted"
                  }`}
                >
                  <div
                    className={`grid h-9 w-9 place-items-center rounded-md ${
                      active ? "bg-primary text-primary-foreground" : "bg-muted text-foreground"
                    }`}
                  >
                    <Icon className="h-4 w-4" />
                  </div>
                  <div>
                    <div className="text-sm font-medium capitalize text-foreground">
                      {mode} mode
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {mode === "light"
                        ? "Warm ivory editorial surface."
                        : "Charcoal surface for low light."}
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </SectionCard>

        {/* Preferences */}
        <SectionCard eyebrow="Preferences" title="Analysis behavior">
          <div className="divide-y divide-border">
            <ToggleRow
              title="Automatically open analysis after processing"
              description="Jump straight into a paper once PaperLens finishes structuring it."
              checked={autoOpen}
              onChange={setAutoOpen}
            />
            <ToggleRow
              title="Show source references"
              description="Display citation cards with page and section for every answer."
              checked={showSources}
              onChange={setShowSources}
            />
            <ToggleRow
              title="Enable chat history"
              description="Keep your questions and answers per paper for later review."
              checked={chatHistory}
              onChange={setChatHistory}
            />
          </div>
        </SectionCard>

        {/* Data */}
        <SectionCard eyebrow="Data" title="Manage your data">
          <div className="divide-y divide-border">
            <div className="flex items-center justify-between gap-4 py-3">
              <div className="min-w-0">
                <div className="text-sm text-foreground">Export workspace</div>
                <div className="mt-0.5 text-xs text-muted-foreground">
                  Download a copy of your papers, notes, and chat history.
                </div>
              </div>
              <button
                type="button"
                className="inline-flex items-center gap-2 rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground hover:bg-muted"
              >
                <Download className="h-4 w-4" />
                Export
              </button>
            </div>
            <div className="flex items-center justify-between gap-4 py-3">
              <div className="min-w-0">
                <div className="text-sm text-foreground">Delete all papers</div>
                <div className="mt-0.5 text-xs text-muted-foreground">
                  Permanently remove every paper and its analysis. This cannot be undone.
                </div>
              </div>
              <button
                type="button"
                onClick={() =>
                  window.confirm("Delete all papers? This will permanently remove your library.")
                }
                className="inline-flex items-center gap-2 rounded-md border border-destructive/40 bg-background px-3 py-2 text-sm text-destructive hover:bg-destructive/10"
              >
                <Trash2 className="h-4 w-4" />
                Delete all
              </button>
            </div>
          </div>
        </SectionCard>

        <div className="flex justify-end gap-2 pb-4">
          <button className="rounded-md border border-border bg-surface px-4 py-2 text-sm text-foreground hover:bg-muted">
            Cancel
          </button>
          <button className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90">
            Save changes
          </button>
        </div>
      </div>
    </AppShell>
  );
}
