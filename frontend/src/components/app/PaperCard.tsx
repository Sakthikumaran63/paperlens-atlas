import { Link } from "@tanstack/react-router";
import { FileText, Users } from "lucide-react";
import type { Paper } from "@/lib/mock-papers";
import { StatusBadge } from "./StatusBadge";

export function PaperCard({ paper }: { paper: Paper }) {
  return (
    <Link
      to="/paper/$id"
      params={{ id: paper.id }}
      className="group flex h-full flex-col rounded-lg border border-border bg-surface p-5 transition hover:border-primary/60 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex h-9 w-7 shrink-0 items-center justify-center rounded-sm border border-border bg-background text-muted-foreground">
          <FileText className="h-3.5 w-3.5" aria-hidden />
        </div>
        <StatusBadge status={paper.status} />
      </div>

      <h3 className="mt-4 font-serif-editorial text-lg leading-snug text-foreground group-hover:text-primary">
        {paper.title}
      </h3>

      <div className="mt-2 flex items-center gap-1.5 text-xs text-muted-foreground">
        <Users className="h-3 w-3" aria-hidden />
        <span className="truncate">
          {paper.authors.slice(0, 2).join(", ")}
          {paper.authors.length > 2 && ` +${paper.authors.length - 2}`}
        </span>
      </div>

      <p className="mt-3 line-clamp-3 text-sm text-muted-foreground">{paper.abstract}</p>

      <div className="mt-auto flex items-center justify-between pt-4 text-xs text-muted-foreground">
        <span>
          {paper.venue} · {paper.year}
        </span>
        <span>{paper.pages} pages</span>
      </div>
    </Link>
  );
}
