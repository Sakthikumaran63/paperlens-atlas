import { createFileRoute } from "@tanstack/react-router";
import { AppShell } from "@/components/app/AppShell";
import { SectionCard } from "@/components/app/SectionCard";
import { UploadZone } from "@/components/app/UploadZone";

export const Route = createFileRoute("/upload")({
  head: () => ({
    meta: [
      { title: "Upload Paper · PaperLens" },
      {
        name: "description",
        content:
          "Upload a research paper PDF to PaperLens to extract its abstract, methodology, and contributions.",
      },
      { property: "og:title", content: "Upload Paper · PaperLens" },
      {
        property: "og:description",
        content: "Add a new paper to your PaperLens library.",
      },
    ],
  }),
  component: UploadPage,
});

function UploadPage() {
  return (
    <AppShell eyebrow="Add to library" title="Upload a paper">
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <SectionCard eyebrow="Step 1" title="Choose a PDF">
            <UploadZone />
          </SectionCard>
        </div>

        <SectionCard eyebrow="What happens next" title="Paper processing">
          <ol className="space-y-4 text-sm text-muted-foreground">
            <li className="flex gap-3">
              <span className="mt-0.5 grid h-5 w-5 shrink-0 place-items-center rounded-full border border-border text-[11px] font-semibold text-foreground">
                1
              </span>
              We parse the PDF and extract structured text sections.
            </li>
            <li className="flex gap-3">
              <span className="mt-0.5 grid h-5 w-5 shrink-0 place-items-center rounded-full border border-border text-[11px] font-semibold text-foreground">
                2
              </span>
              Key contributions, methodology, and results are surfaced automatically.
            </li>
            <li className="flex gap-3">
              <span className="mt-0.5 grid h-5 w-5 shrink-0 place-items-center rounded-full border border-border text-[11px] font-semibold text-foreground">
                3
              </span>
              You can ask grounded questions about the paper in the reader.
            </li>
          </ol>
        </SectionCard>
      </div>
    </AppShell>
  );
}
