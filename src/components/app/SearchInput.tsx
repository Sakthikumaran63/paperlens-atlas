import { Search } from "lucide-react";
import { cn } from "@/lib/utils";

interface Props extends React.InputHTMLAttributes<HTMLInputElement> {
  containerClassName?: string;
}

export function SearchInput({ containerClassName, className, ...props }: Props) {
  return (
    <div
      className={cn(
        "flex items-center gap-2 rounded-md border border-border bg-surface px-3 py-2 text-sm transition focus-within:border-primary focus-within:ring-2 focus-within:ring-primary/20",
        containerClassName,
      )}
    >
      <Search className="h-4 w-4 text-muted-foreground" aria-hidden />
      <input
        type="search"
        className={cn(
          "w-full bg-transparent text-foreground placeholder:text-muted-foreground focus:outline-none",
          className,
        )}
        {...props}
      />
    </div>
  );
}
