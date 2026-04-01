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
    <div className="border-t border-border bg-bg-secondary p-3 shrink-0">
      <div className="max-w-4xl mx-auto">
        <div className="flex items-end gap-2 bg-bg-tertiary rounded-xl border border-border p-2 focus-within:border-accent transition-colors">
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
              "flex-1 bg-transparent text-text-primary text-sm resize-none outline-none placeholder:text-text-muted px-2 py-1 max-h-40",
              "disabled:opacity-50 disabled:cursor-not-allowed"
            )}
          />
          <button
            onClick={handleSend}
            disabled={!text.trim() || isStreaming || disabled}
            className={cn(
              "flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center transition-all",
              text.trim() && !isStreaming && !disabled
                ? "bg-accent hover:bg-accent-hover text-white"
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
        <p className="text-xs text-text-muted mt-2 text-center">
          AI อาจสร้างข้อมูลที่ไม่ถูกต้อง — กรุณาตรวจสอบข้อมูลสำคัญ
        </p>
      </div>
    </div>
  );
}
