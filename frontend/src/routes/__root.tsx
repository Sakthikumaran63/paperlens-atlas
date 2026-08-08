import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  Outlet,
  createRootRouteWithContext,
  useRouter,
  HeadContent,
  Scripts,
} from "@tanstack/react-router";
import { useEffect, type ReactNode } from "react";

import appCss from "../styles.css?url";
import { reportLovableError } from "../lib/lovable-error-reporting";
import { Toaster } from "@/components/ui/sonner";
import { NotFoundView } from "./404";
import { ErrorState } from "@/components/app/states/StatePanels";

function NotFoundComponent() {
  return <NotFoundView />;
}

function ErrorComponent({ error, reset }: { error: Error; reset: () => void }) {
  console.error(error);
  const router = useRouter();
  useEffect(() => {
    reportLovableError(error, { boundary: "tanstack_root_error_component" });
  }, [error]);

  return (
    <div className="flex min-h-dvh items-center justify-center bg-background px-4 py-16">
      <div className="w-full max-w-md">
        <ErrorState
          title="Something went wrong"
          description="We couldn't complete your request. Please try again."
          retryLabel="Try Again"
          onRetry={() => {
            router.invalidate();
            reset();
          }}
          secondaryLabel="Back to Dashboard"
          onSecondary={() => {
            window.location.href = "/dashboard";
          }}
        />
      </div>
    </div>
  );
}

export const Route = createRootRouteWithContext<{ queryClient: QueryClient }>()({
  head: () => ({
    meta: [
      { charSet: "utf-8" },
      { name: "viewport", content: "width=device-width, initial-scale=1" },
      { title: "PaperLens — Read research papers with clarity" },
      {
        name: "description",
        content:
          "PaperLens is an AI research assistant that helps students and academics understand papers, extract methodology, and ask grounded questions.",
      },
      { property: "og:type", content: "website" },
      { property: "og:title", content: "PaperLens — Read research papers with clarity" },
      {
        property: "og:description",
        content:
          "PaperLens is an AI research assistant that helps students and academics understand papers, extract methodology, and ask grounded questions.",
      },
      { name: "twitter:card", content: "summary_large_image" },
      { name: "twitter:title", content: "PaperLens — Read research papers with clarity" },
      {
        name: "twitter:description",
        content:
          "PaperLens is an AI research assistant that helps students and academics understand papers, extract methodology, and ask grounded questions.",
      },
      {
        property: "og:image",
        content:
          "https://pub-bb2e103a32db4e198524a2e9ed8f35b4.r2.dev/002190d0-db5b-4553-9f9c-81e666b799e4/id-preview-a43b5f6f--c23ca41c-568e-463d-87ae-00e1c3114733.lovable.app-1784818746321.png",
      },
      {
        name: "twitter:image",
        content:
          "https://pub-bb2e103a32db4e198524a2e9ed8f35b4.r2.dev/002190d0-db5b-4553-9f9c-81e666b799e4/id-preview-a43b5f6f--c23ca41c-568e-463d-87ae-00e1c3114733.lovable.app-1784818746321.png",
      },
    ],
    links: [
      { rel: "stylesheet", href: appCss },
      { rel: "icon", href: "/favicon.ico", type: "image/x-icon" },
      { rel: "preconnect", href: "https://fonts.googleapis.com" },
      {
        rel: "preconnect",
        href: "https://fonts.gstatic.com",
        crossOrigin: "anonymous",
      },
      {
        rel: "stylesheet",
        href: "https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,400;9..40,500;9..40,600;9..40,700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,500;8..60,600;8..60,700&display=swap",
      },
    ],
  }),
  shellComponent: RootShell,
  component: RootComponent,
  notFoundComponent: NotFoundComponent,
  errorComponent: ErrorComponent,
});

function RootShell({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <head>
        <HeadContent />
      </head>
      <body>
        {children}
        <Scripts />
      </body>
    </html>
  );
}

function RootComponent() {
  const { queryClient } = Route.useRouteContext();

  return (
    <QueryClientProvider client={queryClient}>
      <Outlet />
      <Toaster
        position="top-right"
        richColors={false}
        closeButton
        mobileOffset={{ bottom: "16px" }}
      />
    </QueryClientProvider>
  );
}
