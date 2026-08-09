import { useState } from "react";
import { Link, useRouterState } from "@tanstack/react-router";
import {
  LayoutGrid,
  Library,
  UploadCloud,
  Clock,
  Settings,
  LifeBuoy,
  User,
  ShieldCheck,
  LogIn,
  type LucideIcon,
} from "lucide-react";
import { Logo } from "@/components/brand/Logo";
import { cn } from "@/lib/utils";
import { AuthModal } from "./AuthModal";
import { AdminModal } from "./AdminModal";


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
  { label: "Profile", to: "/profile", icon: User },
  { label: "Settings", to: "/settings", icon: Settings },
  { label: "Help", to: "/help", icon: LifeBuoy },
];

function NavRow({ item, active }: { item: Item; active: boolean }) {
  const Icon = item.icon;
  return (
    <Link
      to={item.to}
      className={cn(
        "group relative flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40",
        active
          ? "bg-accent text-primary"
          : "text-foreground/80 hover:bg-muted hover:text-foreground",
      )}
    >
      {active && (
        <span aria-hidden className="absolute inset-y-1.5 left-0 w-0.5 rounded-r-sm bg-primary" />
      )}
      <Icon
        className={cn(
          "h-4 w-4 shrink-0 transition-colors",
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
  const [authOpen, setAuthOpen] = useState(false);
  const [adminOpen, setAdminOpen] = useState(false);
  const [currentUser, setCurrentUser] = useState<any>(() => {
    if (typeof window === "undefined") {
      return { email: "kkssakthikumaran@gmail.com", name: "Sakthi Kumaran", is_admin: true };
    }
    const cached = localStorage.getItem("paperlens_user");
    return cached ? JSON.parse(cached) : { email: "kkssakthikumaran@gmail.com", name: "Sakthi Kumaran", is_admin: true };
  });

  const isActive = (to: string) =>
    to === "/dashboard" ? pathname === "/dashboard" || pathname === "/" : pathname.startsWith(to);

  const isAdmin = currentUser?.email?.toLowerCase() === "kkssakthikumaran@gmail.com" || currentUser?.is_admin;

  return (
    <>
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

        <div className="border-t border-border px-3 py-4 space-y-2">
          {isAdmin && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                setAdminOpen(true);
              }}
              className="flex w-full items-center gap-2.5 rounded-md border border-primary/30 bg-primary/10 px-3 py-2 text-xs font-semibold text-primary hover:bg-primary/20 transition-colors"
            >
              <ShieldCheck className="h-4 w-4" />
              <span>Admin Panel</span>
            </button>
          )}

          <nav className="space-y-0.5">
            {secondary.map((item) => (
              <NavRow key={item.to} item={item} active={isActive(item.to)} />
            ))}
          </nav>

          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              setAuthOpen(true);
            }}
            className="flex w-full items-center gap-3 rounded-md border border-border bg-background px-3 py-2.5 transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40 text-left"
          >
            <div className="grid h-8 w-8 shrink-0 place-items-center rounded-md border border-border bg-surface text-[11px] font-semibold tracking-wide text-foreground uppercase">
              {currentUser?.name ? currentUser.name.slice(0, 2) : "SK"}
            </div>
            <div className="min-w-0 flex-1 leading-tight">
              <div className="truncate text-sm font-medium text-foreground">
                {currentUser?.name || "Sakthi Kumaran"}
              </div>
              <div className="truncate text-xs text-muted-foreground">
                {isAdmin ? "System Administrator" : "Research Fellow"}
              </div>
            </div>
            <LogIn className="h-4 w-4 text-muted-foreground shrink-0" />
          </button>
        </div>
      </aside>

      <AuthModal
        isOpen={authOpen}
        onClose={() => setAuthOpen(false)}
        onSuccess={(user) => {
          setCurrentUser(user);
          localStorage.setItem("paperlens_user", JSON.stringify(user));
        }}
      />

      <AdminModal
        isOpen={adminOpen}
        onClose={() => setAdminOpen(false)}
      />
    </>
  );
}

