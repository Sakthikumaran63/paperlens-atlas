import { useState, useCallback } from "react";
import { UploadCloud, FileText, X } from "lucide-react";
import { cn } from "@/lib/utils";

interface MockFile {
  id: string;
  name: string;
  size: string;
  progress: number;
}

export function UploadZone() {
  const [dragOver, setDragOver] = useState(false);
  const [files, setFiles] = useState<MockFile[]>([]);

  const addMockFile = useCallback((name: string) => {
    const id = Math.random().toString(36).slice(2);
    const f: MockFile = {
      id,
      name,
      size: `${(Math.random() * 4 + 0.5).toFixed(1)} MB`,
      progress: 0,
    };
    setFiles((prev) => [...prev, f]);
    const step = () => {
      setFiles((prev) =>
        prev.map((x) => (x.id === id ? { ...x, progress: Math.min(100, x.progress + 12) } : x)),
      );
    };
    const iv = setInterval(() => {
      setFiles((prev) => {
        const target = prev.find((x) => x.id === id);
        if (!target || target.progress >= 100) {
          clearInterval(iv);
          return prev;
        }
        return prev;
      });
      step();
    }, 220);
  }, []);

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const dropped = Array.from(e.dataTransfer.files);
    if (dropped.length === 0) addMockFile("uploaded-paper.pdf");
    else dropped.forEach((f) => addMockFile(f.name));
  };

  return (
    <div className="space-y-4">
      <label
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        className={cn(
          "flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed bg-surface px-6 py-14 text-center transition",
          dragOver ? "border-primary bg-accent/40" : "border-border hover:border-primary/60",
        )}
      >
        <div className="grid h-12 w-12 place-items-center rounded-full border border-border bg-background text-primary">
          <UploadCloud className="h-5 w-5" aria-hidden />
        </div>
        <div className="mt-4 font-serif-editorial text-lg text-foreground">
          Drop a research paper here
        </div>
        <p className="mt-1 text-sm text-muted-foreground">
          PDF up to 25 MB · or click to browse your files
        </p>
        <input
          type="file"
          accept="application/pdf"
          multiple
          className="sr-only"
          onChange={(e) => {
            const list = Array.from(e.target.files ?? []);
            list.forEach((f) => addMockFile(f.name));
            e.currentTarget.value = "";
          }}
        />
      </label>

      {files.length > 0 && (
        <ul className="divide-y divide-border rounded-lg border border-border bg-surface">
          {files.map((f) => (
            <li key={f.id} className="flex items-center gap-3 px-4 py-3">
              <div className="grid h-9 w-7 shrink-0 place-items-center rounded-sm border border-border bg-background text-muted-foreground">
                <FileText className="h-3.5 w-3.5" aria-hidden />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between gap-2">
                  <span className="truncate text-sm text-foreground">{f.name}</span>
                  <span className="text-xs text-muted-foreground">{f.size}</span>
                </div>
                <div className="mt-2 h-1 overflow-hidden rounded-full bg-muted">
                  <div
                    className="h-full rounded-full bg-primary transition-[width] duration-300"
                    style={{ width: `${f.progress}%` }}
                  />
                </div>
                <div className="mt-1 text-[11px] text-muted-foreground">
                  {f.progress < 100 ? `Analyzing… ${f.progress}%` : "Ready for review"}
                </div>
              </div>
              <button
                type="button"
                onClick={() => setFiles((prev) => prev.filter((x) => x.id !== f.id))}
                aria-label={`Remove ${f.name}`}
                className="rounded-md p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
              >
                <X className="h-4 w-4" />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
