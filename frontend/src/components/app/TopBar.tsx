import { Bell, Menu } from "lucide-react";
import { SearchInput } from "./SearchInput";

interface Props {
  title: string;
  eyebrow?: string;
  onToggleSidebar?: () => void;
}

export function TopBar({ title, eyebrow, onToggleSidebar }: Props) {
  return (
    <header className="sticky top-0 z-20 flex h-16 items-center gap-3 border-b border-border bg-background/85 px-4 backdrop-blur md:px-8">
      <button
        type="button"
        onClick={onToggleSidebar}
        aria-label="Open navigation"
        className="grid h-9 w-9 place-items-center rounded-md border border-border text-foreground md:hidden"
      >
        <Menu className="h-4 w-4" />
      </button>

      <div className="min-w-0 flex-1">
        {eyebrow && (
          <div className="text-[0.65rem] font-medium uppercase tracking-[0.16em] text-muted-foreground">
            {eyebrow}
          </div>
        )}
        <h1 className="truncate font-serif-editorial text-xl text-foreground md:text-2xl">
          {title}
        </h1>
      </div>

      <div className="hidden w-72 md:block">
        <SearchInput placeholder="Search papers, authors, notes…" />
      </div>

      <button
        type="button"
        aria-label="Notifications"
        className="grid h-9 w-9 shrink-0 place-items-center rounded-md border border-border text-muted-foreground hover:text-foreground"
      >
        <Bell className="h-4 w-4" />
      </button>

      <div className="hidden h-9 w-9 shrink-0 place-items-center rounded-full bg-primary text-xs font-semibold text-primary-foreground md:grid">
        AR
      </div>
    </header>
  );
}
