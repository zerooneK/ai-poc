"use client";

import { useState, useCallback } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { X, Copy, FileText, Code } from "lucide-react";
import { cn, fileIcon } from "@/lib/utils";
import { getPreview } from "@/lib/api";

interface PreviewPanelProps {
  filename: string | null;
  onClose: () => void;
}

export default function PreviewPanel({ filename, onClose }: PreviewPanelProps) {
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<"rendered" | "raw">("rendered");

  const loadContent = useCallback(() => {
    if (!filename) return;
    setLoading(true);
    setError(null);
    setContent("");
    getPreview(filename)
      .then((res) => {
        setContent(res.content);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, [filename]);

  loadContent();

  if (!filename) return null;

  const ext = filename.split(".").pop()?.toLowerCase() || "";
  const isMarkdown = ["md", "txt"].includes(ext);

  const handleCopy = () => {
    navigator.clipboard.writeText(content);
  };

  return (
    <div className="fixed inset-y-0 right-0 w-[420px] bg-bg-secondary border-l border-border flex flex-col z-40 shadow-xl">
      <div className="flex items-center justify-between px-4 py-3 border-b border-border shrink-0">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-lg">{fileIcon(filename)}</span>
          <span className="text-sm font-medium text-text-primary truncate">
            {filename}
          </span>
        </div>
        <button
          onClick={onClose}
          className="p-1 rounded hover:bg-bg-hover text-text-muted transition-colors"
          aria-label="ปิด preview"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {isMarkdown && (
        <div className="flex border-b border-border shrink-0">
          <button
            onClick={() => setViewMode("rendered")}
            className={cn(
              "flex items-center gap-1.5 px-4 py-2 text-xs font-medium border-b-2 transition-colors",
              viewMode === "rendered"
                ? "border-accent text-accent"
                : "border-transparent text-text-muted hover:text-text-secondary"
            )}
          >
            <FileText className="w-3.5 h-3.5" />
            แสดงผล
          </button>
          <button
            onClick={() => setViewMode("raw")}
            className={cn(
              "flex items-center gap-1.5 px-4 py-2 text-xs font-medium border-b-2 transition-colors",
              viewMode === "raw"
                ? "border-accent text-accent"
                : "border-transparent text-text-muted hover:text-text-secondary"
            )}
          >
            <Code className="w-3.5 h-3.5" />
            ข้อความ
          </button>
        </div>
      )}

      <div className="flex-1 overflow-y-auto p-4">
        {loading && (
          <div className="flex items-center justify-center h-full text-text-muted">
            <span className="text-sm">กำลังโหลด...</span>
          </div>
        )}
        {error && (
          <div className="text-error text-sm text-center mt-8">❌ {error}</div>
        )}
        {!loading && !error && content && (
          <>
            {viewMode === "rendered" && isMarkdown ? (
              <div
                className="prose prose-invert prose-sm max-w-none
                  prose-headings:text-text-primary
                  prose-p:text-text-primary
                  prose-code:text-accent
                  prose-pre:bg-bg-primary
                  prose-pre:border prose-pre:border-border
                  prose-strong:text-text-primary
                  prose-a:text-text-link
                  prose-li:text-text-primary"
              >
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {content}
                </ReactMarkdown>
              </div>
            ) : (
              <pre className="text-xs text-text-primary whitespace-pre-wrap font-mono bg-bg-primary rounded-lg p-4 border border-border">
                {content}
              </pre>
            )}
          </>
        )}
        {!loading && !error && !content && (
          <div className="text-text-muted text-sm text-center mt-8">
            ไม่มีเนื้อหา
          </div>
        )}
      </div>

      <div className="flex items-center justify-between px-4 py-2 border-t border-border shrink-0">
        <span className="text-xs text-text-muted">
          {(content.length / 1024).toFixed(1)} KB
        </span>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-text-secondary hover:text-text-primary bg-bg-tertiary hover:bg-bg-hover rounded transition-colors"
        >
          <Copy className="w-3.5 h-3.5" />
          คัดลอก
        </button>
      </div>
    </div>
  );
}
