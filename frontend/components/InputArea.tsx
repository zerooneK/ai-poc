"use client";

import { useState, useRef, useCallback, KeyboardEvent } from "react";
import { Send, Loader2 } from "lucide-react";
import { cn, fileIcon, formatBytes } from "@/lib/utils";

interface WorkspaceFile {
  name: string;
  size: number;
  modified: string;
}

interface InputAreaProps {
  onSend: (message: string) => void;
  isStreaming: boolean;
  disabled?: boolean;
  files?: WorkspaceFile[];
}

interface MentionState {
  query: string;
  atIndex: number;
  selectedIndex: number;
}

export default function InputArea({
  onSend,
  isStreaming,
  disabled = false,
  files = [],
}: InputAreaProps) {
  const [text, setText] = useState("");
  const [mention, setMention] = useState<MentionState | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const filteredFiles = mention
    ? files
        .filter((f) => f.name.toLowerCase().includes(mention.query.toLowerCase()))
        .slice(0, 8)
    : [];

  const closeMention = useCallback(() => setMention(null), []);

  const selectFile = useCallback(
    (filename: string) => {
      if (!mention) return;
      const before = text.slice(0, mention.atIndex);
      const rawAfter = text.slice(mention.atIndex + mention.query.length + 1);
      const after = rawAfter.startsWith(" ") ? rawAfter : " " + rawAfter;
      const newText = (before + "@" + filename + after).trimEnd() + " ";
      setText(newText);
      closeMention();
      requestAnimationFrame(() => {
        const el = textareaRef.current;
        if (!el) return;
        el.focus();
        const pos = before.length + filename.length + 2;
        el.setSelectionRange(pos, pos);
        el.style.height = "auto";
        el.style.height = Math.min(el.scrollHeight, 160) + "px";
      });
    },
    [mention, text, closeMention]
  );

  const handleSend = useCallback(() => {
    const trimmed = text.trim();
    if (!trimmed || isStreaming || disabled) return;
    onSend(trimmed);
    setText("");
    closeMention();
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  }, [closeMention, disabled, isStreaming, onSend, text]);

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (mention && filteredFiles.length > 0) {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setMention((prev) =>
          prev
            ? { ...prev, selectedIndex: Math.min(prev.selectedIndex + 1, filteredFiles.length - 1) }
            : prev
        );
        return;
      }
      if (e.key === "ArrowUp") {
        e.preventDefault();
        setMention((prev) =>
          prev ? { ...prev, selectedIndex: Math.max(prev.selectedIndex - 1, 0) } : prev
        );
        return;
      }
      if (e.key === "Enter" || e.key === "Tab") {
        e.preventDefault();
        selectFile(filteredFiles[mention.selectedIndex].name);
        return;
      }
      if (e.key === "Escape") {
        e.preventDefault();
        closeMention();
        return;
      }
    }

    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value;
    const cursor = e.target.selectionStart ?? value.length;
    const textBeforeCursor = value.slice(0, cursor);
    const atMatch = textBeforeCursor.match(/@(\S*)$/);

    if (atMatch && files.length > 0) {
      setMention({
        query: atMatch[1],
        atIndex: cursor - atMatch[0].length,
        selectedIndex: 0,
      });
    } else {
      closeMention();
    }

    setText(value);
  };

  const handleInput = () => {
    const el = textareaRef.current;
    if (el) {
      el.style.height = "auto";
      el.style.height = Math.min(el.scrollHeight, 160) + "px";
    }
  };

  const isDisabled = disabled || isStreaming;

  return (
    <div className="shrink-0 px-4 pb-5 pt-3">
      <div className="mx-auto max-w-4xl relative">
        {/* @mention dropdown — appears above the input */}
        {mention && filteredFiles.length > 0 && (
          <div className="absolute bottom-full left-0 right-0 mb-2 rounded-2xl border border-border bg-bg-secondary shadow-xl overflow-hidden z-50">
            <div className="px-3 py-2 border-b border-border">
              <span className="text-[10px] uppercase tracking-[0.16em] text-text-muted font-medium">
                ไฟล์ในพื้นที่ทำงาน
              </span>
            </div>
            <div className="max-h-52 overflow-y-auto">
              {filteredFiles.map((f, i) => (
                <button
                  key={f.name}
                  type="button"
                  onMouseDown={(e) => {
                    e.preventDefault();
                    selectFile(f.name);
                  }}
                  className={cn(
                    "w-full flex items-center gap-3 px-4 py-2.5 text-sm text-left transition-colors",
                    i === mention.selectedIndex
                      ? "bg-accent/10 text-accent"
                      : "text-text-primary hover:bg-bg-hover"
                  )}
                >
                  <span className="text-base shrink-0">{fileIcon(f.name)}</span>
                  <span className="flex-1 truncate font-medium">{f.name}</span>
                  <span className="text-xs text-text-muted shrink-0">
                    {formatBytes(f.size)}
                  </span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Input card */}
        <div className="rounded-[28px] border border-border-light bg-surface-elevated/80 p-3 shadow-ambient backdrop-blur-2xl">
          <div className="flex items-end gap-3 rounded-[24px] bg-bg-tertiary px-3 py-2 transition-all ring-1 ring-transparent focus-within:ring-accent/40 focus-within:shadow-[0_0_8px_rgba(0,108,82,0.4)]">
            <textarea
              ref={textareaRef}
              value={text}
              onChange={handleChange}
              onKeyDown={handleKeyDown}
              onInput={handleInput}
              placeholder={
                files.length > 0
                  ? "พิมพ์ข้อความ... (ใช้ @ เพื่ออ้างอิงไฟล์)"
                  : "พิมพ์ข้อความ..."
              }
              rows={1}
              disabled={isDisabled}
              className={cn(
                "min-h-[28px] flex-1 bg-transparent px-1 py-1 text-sm text-text-primary resize-none outline-none placeholder:text-text-muted max-h-40",
                "disabled:opacity-50 disabled:cursor-not-allowed"
              )}
            />
            <button
              onClick={handleSend}
              disabled={!text.trim() || isDisabled}
              className={cn(
                "flex h-10 w-10 shrink-0 items-center justify-center rounded-full transition-all shadow-sm",
                text.trim() && !isDisabled
                  ? "bg-gradient-to-br from-accent to-accent-hover text-white hover:scale-[0.98] hover:shadow-ambient"
                  : "bg-bg-hover text-text-muted cursor-not-allowed"
              )}
              aria-label="ส่งข้อความ"
            >
              {isStreaming ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Send className="w-4 h-4" />
              )}
            </button>
          </div>
          <div className="mt-3 flex items-center justify-between gap-3 px-1">
            <p className="text-xs text-text-muted">
              AI อาจสร้างข้อมูลที่ไม่ถูกต้อง กรุณาตรวจสอบข้อมูลสำคัญ
            </p>
            <span className="hidden text-[11px] uppercase tracking-[0.18em] text-text-muted sm:block">
              {files.length > 0 ? "Enter ส่ง · @ แนบไฟล์" : "Enter เพื่อส่ง"}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
