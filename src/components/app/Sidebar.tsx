import { Link, useRouterState } from "@tanstack/react-router";
import {
  LayoutGrid,
  Library,
  UploadCloud,
  Clock,
  Settings,
  LifeBuoy,
  type LucideIcon,
} from "lucide-react";
import { Logo } from "@/components/brand/Logo";
import { cn } from "@/lib/utils";

interface Item {
  label: string;
  to: string;
  icon: LucideIcon;
}

const primary: Item[] = [
  { label: "Overview", to: "/dashboard", icon: LayoutGrid },
  { label: "My Papers", to: "/papers", icon: Library },
  { label: "Upload Paper", to: "/upload", icon: UploadCloud },
  { label: "Recent Activity", to: "/activity", icon: Clock },
];

const secondary: Item[] = [
  { label: "Settings", to: "/settings", icon: Settings },
  { label: "Help", to: "/help", icon: LifeBuoy },
];

function NavRow({ item, active }: { item: Item; active: boolean }) {
  const Icon = item.icon;
  return (
    <Link
      to={item.to}
      className={cn(
        "group flex items-center gap-3 rounded-md px-3 py-2 text-sm transition",
        active
          ? "bg-accent text-primary"
          : "text-foreground/80 hover:bg-muted hover:text-foreground",
      )}
    >
      <Icon
        className={cn(
          "h-4 w-4 shrink-0",
          active ? "text-primary" : "text-muted-foreground group-hover:text-foreground",
        )}
        aria-hidden
      />
      <span className="truncate">{item.label}</span>
    </Link>
  );
}

export function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const isActive = (to: string) =>
    to === "/dashboard" ? pathname === "/dashboard" || pathname === "/" : pathname.startsWith(to);

  return (
    <aside
      className="flex h-full w-full flex-col border-r border-border bg-surface"
      onClick={onNavigate}
    >
      <div className="flex h-16 items-center border-b border-border px-5">
        <Logo />
      </div>

      <div className="flex-1 overflow-y-auto px-3 py-5">
        <div className="mb-2 px-3 text-[0.65rem] font-medium uppercase tracking-[0.16em] text-muted-foreground">
          Workspace
        </div>
        <nav className="space-y-0.5">
          {primary.map((item) => (
            <NavRow key={item.to} item={item} active={isActive(item.to)} />
          ))}
        </nav>
      </div>

      <div className="border-t border-border px-3 py-4">
        <nav className="space-y-0.5">
          {secondary.map((item) => (
            <NavRow key={item.to} item={item} active={isActive(item.to)} />
          ))}
        </nav>
        <div className="mt-4 flex items-center gap-3 rounded-md border border-border bg-background px-3 py-2.5">
          <div className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-primary text-xs font-semibold text-primary-foreground">
            AR
          </div>
          <div className="min-w-0 leading-tight">
            <div className="truncate text-sm font-medium text-foreground">Aria Ren</div>
            <div className="truncate text-xs text-muted-foreground">Research fellow</div>
          </div>
        </div>
      </div>
    </aside>
  );
}
