"use client";

import { useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { X, Copy, FileText, Code, Pencil } from "lucide-react";
import { cn, fileIcon } from "@/lib/utils";
import { getPreviewForSession, getFileUrlForSession } from "@/lib/api";

const PdfViewer = dynamic(() => import("./PdfViewer"), { ssr: false });

interface SelectionPopup {
  top: number;
  left: number;
  text: string;
}

interface PreviewPanelProps {
  filename: string | null;
  sessionId?: string;
  refreshKey?: number;
  onClose: () => void;
  onEditSelection?: (data: { prefill: string; filename: string; originalText: string }) => void;
}

export default function PreviewPanel({ filename, sessionId, refreshKey, onClose, onEditSelection }: PreviewPanelProps) {
  const [content, setContent] = useState("");
  const [size, setSize] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loadedFilename, setLoadedFilename] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<"rendered" | "raw">("rendered");
  const [selectionPopup, setSelectionPopup] = useState<SelectionPopup | null>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  const ext = filename?.split(".").pop()?.toLowerCase() || "";
  const isPdf = ext === "pdf";
  // docx/xlsx store markdown text internally — render as formatted, not raw
  const isMarkdown = ["md", "txt", "docx", "xlsx"].includes(ext);

  // Load text file content — re-fetches when refreshKey changes (after partial replace)
  useEffect(() => {
    if (!filename || isPdf) return;
    let cancelled = false;
    setContent("");
    setError(null);
    setLoadedFilename(null);
    getPreviewForSession(filename, sessionId)
      .then((res) => {
        if (cancelled) return;
        setContent(res.content);
        setSize(res.size ?? null);
        setError(null);
        setLoadedFilename(filename);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err.message);
        setLoadedFilename(filename);
      });
    return () => { cancelled = true; };
  }, [filename, sessionId, isPdf, refreshKey]);

  if (!filename) return null;

  const loading = !isPdf && loadedFilename !== filename && !error;

  const handleCopy = () => navigator.clipboard.writeText(content);

  const handleMouseUp = () => {
    if (!onEditSelection) return;
    // Only allow partial edit from raw view — rendered markdown text differs from file content
    if (isMarkdown && viewMode === "rendered") return;
    const sel = window.getSelection();
    if (!sel || sel.isCollapsed) {
      setSelectionPopup(null);
      return;
    }
    const text = sel.toString().trim();
    if (!text) {
      setSelectionPopup(null);
      return;
    }
    const range = sel.getRangeAt(0);
    const rect = range.getBoundingClientRect();
    const panelRect = panelRef.current?.getBoundingClientRect();
    if (!panelRect) return;
    setSelectionPopup({
      top: rect.bottom - panelRect.top + 8,
      left: Math.min(
        rect.left - panelRect.left + rect.width / 2,
        panelRect.width - 140
      ),
      text,
    });
  };

  const handleEditSelection = () => {
    if (!selectionPopup || !onEditSelection || !filename) return;
    const prefill = `[PARTIAL_EDIT] @${filename}\n"""\n${selectionPopup.text}\n"""\nแก้ไขโดย: `;
    onEditSelection({ prefill, filename, originalText: selectionPopup.text });
    setSelectionPopup(null);
    window.getSelection()?.removeAllRanges();
  };

  return (
    <div
      ref={panelRef}
      className="fixed inset-0 sm:inset-y-0 sm:left-auto sm:right-0 sm:w-[380px] lg:w-[420px] bg-bg-secondary border-l border-border flex flex-col z-40 shadow-xl"
      onMouseUp={handleMouseUp}
    >
      {/* Header */}
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

      {/* Tabs (markdown/txt only) */}
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

      {/* Body */}
      {isPdf ? (
        <div className="flex-1 flex flex-col overflow-hidden">
          <PdfViewer url={getFileUrlForSession(filename, sessionId)} />
        </div>
      ) : (
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
      )}

      {/* Selection popup */}
      {selectionPopup && onEditSelection && (
        <button
          onMouseDown={(e) => e.preventDefault()}
          onClick={handleEditSelection}
          style={{ top: selectionPopup.top, left: selectionPopup.left }}
          className="absolute z-50 -translate-x-1/2 flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-accent text-white text-xs font-medium shadow-lg hover:bg-accent-hover transition-colors"
        >
          <Pencil className="w-3 h-3" />
          แก้ไขส่วนนี้
        </button>
      )}

      {/* Footer (text files only) */}
      {!isPdf && (
        <div className="flex items-center justify-between px-4 py-2 border-t border-border shrink-0">
          <span className="text-xs text-text-muted">
            {size != null ? (size / 1024).toFixed(1) : (content.length / 1024).toFixed(1)} KB
          </span>
          <button
            onClick={handleCopy}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-text-secondary hover:text-text-primary bg-bg-tertiary hover:bg-bg-hover rounded transition-colors"
          >
            <Copy className="w-3.5 h-3.5" />
            คัดลอก
          </button>
        </div>
      )}
    </div>
  );
}
