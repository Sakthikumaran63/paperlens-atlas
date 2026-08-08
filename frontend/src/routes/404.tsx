import { createFileRoute, Link } from "@tanstack/react-router";
import { DocumentMark } from "@/components/app/states/StatePanels";

export const Route = createFileRoute("/404")({
  head: () => ({
    meta: [
      { title: "Page not found · PaperLens" },
      { name: "robots", content: "noindex" },
      { name: "description", content: "The page you're looking for doesn't exist." },
    ],
  }),
  component: NotFoundPage,
});

function NotFoundPage() {
  return <NotFoundView />;
}

export function NotFoundView() {
  return (
    <div className="flex min-h-dvh items-center justify-center bg-background px-4 py-16">
      <div className="mx-auto flex w-full max-w-md flex-col items-center text-center">
        <DocumentMark variant="torn" />
        <div
          aria-hidden
          className="mt-6 font-serif-editorial text-6xl leading-none tracking-tight text-foreground md:text-7xl"
        >
          404
        </div>
        <h1 className="mt-4 font-serif-editorial text-2xl text-foreground">Page not found</h1>
        <p className="mt-2 max-w-sm text-sm text-muted-foreground">
          The page you're looking for doesn't exist or may have been moved.
        </p>
        <div className="mt-7 flex w-full flex-col-reverse gap-2 sm:w-auto sm:flex-row">
          <Link
            to="/papers"
            className="inline-flex items-center justify-center rounded-md border border-border bg-surface px-4 py-2 text-sm text-foreground hover:bg-muted"
          >
            Go to My Papers
          </Link>
          <Link
            to="/dashboard"
            className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
          >
            Back to Dashboard
          </Link>
        </div>
      </div>
    </div>
  );
}
