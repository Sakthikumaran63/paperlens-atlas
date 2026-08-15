import { useEffect, useState } from "react";
import { Moon, Sun } from "lucide-react";
import { applyTheme, getStoredTheme, type ThemeMode } from "@/lib/theme";

export function ThemeToggle({ className }: { className?: string }) {
  const [theme, setThemeState] = useState<ThemeMode>("light");

  useEffect(() => {
    const current = getStoredTheme();
    setThemeState(current);
    applyTheme(current);
  }, []);

  const toggleTheme = () => {
    const nextTheme: ThemeMode = theme === "light" ? "dark" : "light";
    setThemeState(nextTheme);
    applyTheme(nextTheme);
  };

  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-label={`Switch to ${theme === "light" ? "dark" : "light"} mode`}
      title={`Switch to ${theme === "light" ? "dark" : "light"} mode`}
      className={`grid h-9 w-9 shrink-0 place-items-center rounded-md border border-border bg-background text-muted-foreground hover:bg-muted hover:text-foreground transition-colors ${className || ""}`}
    >
      {theme === "light" ? (
        <Moon className="h-4 w-4 text-foreground" />
      ) : (
        <Sun className="h-4 w-4 text-amber-400" />
      )}
    </button>
  );
}
