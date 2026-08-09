export function Logo({ collapsed = false }: { collapsed?: boolean }) {
  return (
    <div className="flex items-center gap-2">
      <img
        src="/paperlens-logo.svg"
        alt="PaperLens Logo"
        width="28"
        height="28"
        className="shrink-0"
        aria-hidden="true"
      />
      {!collapsed && (
        <span className="font-serif-editorial text-[1.05rem] font-semibold tracking-tight text-foreground">
          Paper<span className="text-primary">Lens</span>
        </span>
      )}
    </div>
  );
}
