export function Logo({ collapsed = false }: { collapsed?: boolean }) {
  return (
    <div className="flex items-center gap-2">
      <svg
        width="22"
        height="22"
        viewBox="0 0 22 22"
        fill="none"
        aria-hidden="true"
        className="shrink-0"
      >
        <rect
          x="3.5"
          y="2.5"
          width="12"
          height="16"
          rx="1"
          stroke="currentColor"
          strokeWidth="1.4"
        />
        <path
          d="M6.5 3v16l3-2 3 2V3"
          stroke="var(--terracotta)"
          strokeWidth="1.4"
          strokeLinejoin="round"
          fill="none"
        />
        <circle cx="16" cy="16" r="3.2" stroke="currentColor" strokeWidth="1.4" />
      </svg>
      {!collapsed && (
        <span className="font-serif-editorial text-[1.05rem] font-semibold tracking-tight text-foreground">
          Paper<span className="text-primary">Lens</span>
        </span>
      )}
    </div>
  );
}
