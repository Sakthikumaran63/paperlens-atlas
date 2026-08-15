// PaperLens Centralized Theme Management Utility (Dark & Light Mode)

export type ThemeMode = "light" | "dark";

const THEME_KEY = "paperlens_theme";

export function getStoredTheme(): ThemeMode {
  if (typeof window === "undefined") return "light";
  const stored = localStorage.getItem(THEME_KEY);
  if (stored === "dark" || stored === "light") {
    return stored;
  }
  // Default to system preference if present, otherwise light
  if (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches) {
    return "dark";
  }
  return "light";
}

export function applyTheme(mode: ThemeMode): void {
  if (typeof window === "undefined") return;
  
  const root = document.documentElement;
  if (mode === "dark") {
    root.classList.add("dark");
  } else {
    root.classList.remove("dark");
  }
  localStorage.setItem(THEME_KEY, mode);
}

export function initTheme(): ThemeMode {
  const current = getStoredTheme();
  applyTheme(current);
  return current;
}
