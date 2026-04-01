"use client";

import { useState, useRef, KeyboardEvent } from "react";
import { Send, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface InputAreaProps {
  onSend: (message: string) => void;
  isStreaming: boolean;
  disabled?: boolean;
}

export default function InputArea({
  onSend,
  isStreaming,
  disabled = false,
}: InputAreaProps) {
  const [text, setText] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = () => {
    const trimmed = text.trim();
    if (!trimmed || isStreaming || disabled) return;
    onSend(trimmed);
    setText("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInput = () => {
    const el = textareaRef.current;
    if (el) {
      el.style.height = "auto";
      el.style.height = Math.min(el.scrollHeight, 160) + "px";
    }
  };

  return (
    <div className="shrink-0 px-4 pb-5 pt-3">
      <div className="mx-auto max-w-4xl rounded-[28px] border border-border bg-surface-strong/90 p-3 shadow-[0_20px_60px_rgba(15,23,42,0.12)] backdrop-blur-xl">
        <div className="flex items-end gap-3 rounded-2xl border border-border-light bg-bg-tertiary/60 px-3 py-2 transition-colors focus-within:border-accent">
          <textarea
            ref={textareaRef}
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={handleKeyDown}
            onInput={handleInput}
            placeholder="พิมพ์ข้อความ..."
            rows={1}
            disabled={disabled || isStreaming}
            className={cn(
              "min-h-[28px] flex-1 bg-transparent px-1 py-1 text-sm text-text-primary resize-none outline-none placeholder:text-text-muted max-h-40",
              "disabled:opacity-50 disabled:cursor-not-allowed"
            )}
          />
          <button
            onClick={handleSend}
            disabled={!text.trim() || isStreaming || disabled}
            className={cn(
              "flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl transition-all shadow-sm",
              text.trim() && !isStreaming && !disabled
                ? "bg-accent text-white hover:bg-accent-hover hover:shadow-[0_10px_24px_rgba(45,108,223,0.28)]"
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
            Enter เพื่อส่ง
          </span>
        </div>
      </div>
    </div>
  );
}
