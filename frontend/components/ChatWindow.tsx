"use client";

import { useRef, useEffect } from "react";
import MessageBubble from "./MessageBubble";
import { cn } from "@/lib/utils";

interface Message {
  role: "user" | "assistant";
  content: string;
  agent?: string;
}

interface ChatWindowProps {
  messages: Message[];
  isStreaming: boolean;
  statusMessage: string;
  hasError: boolean;
  errorMessage: string | null;
  isEmpty: boolean;
  onQuickAction: (prompt: string) => void;
}

const QUICK_ACTIONS = [
  { label: "👤 สร้างเอกสาร HR", prompt: "ช่วยสร้างเอกสาร HR ให้หน่อย" },
  { label: "💰 สร้างรายงานการเงิน", prompt: "ช่วยสร้างรายงานการเงินให้หน่อย" },
  { label: "📋 คำแนะนำการจัดการ", prompt: "ช่วยให้คำแนะนำด้านการจัดการทีม" },
  { label: "💬 สนทนาทั่วไป", prompt: "มาคุยกันทั่วไป" },
];

export default function ChatWindow({
  messages,
  isStreaming,
  statusMessage,
  hasError,
  errorMessage,
  isEmpty,
  onQuickAction,
}: ChatWindowProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, statusMessage]);

  if (isEmpty) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center px-4">
        <div className="text-5xl mb-4">🤖</div>
        <h2 className="text-xl font-semibold text-text-primary mb-2">
          สวัสดี! มีอะไรให้ช่วยไหม?
        </h2>
        <p className="text-text-secondary text-sm max-w-md">
          พิมพ์ข้อความเพื่อเริ่มใช้งาน — ระบบจะเลือก agent ที่เหมาะสมให้อัตโนมัติ
        </p>
        <div className="mt-8 grid grid-cols-2 gap-3 text-xs text-text-muted">
          {QUICK_ACTIONS.map((action) => (
            <button
              key={action.label}
              onClick={() => onQuickAction(action.prompt)}
              className="rounded-lg bg-bg-tertiary px-4 py-3 text-left transition-colors hover:bg-bg-hover hover:text-text-primary"
              type="button"
            >
              {action.label}
            </button>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Status bar */}
      {(statusMessage || hasError) && (
        <div
          className={cn(
            "flex items-center gap-2 px-4 py-2 text-xs border-b border-border shrink-0",
            hasError ? "bg-error/10 text-error" : "bg-bg-secondary text-text-secondary"
          )}
        >
          {hasError ? (
            <>❌ {errorMessage || statusMessage}</>
          ) : isStreaming ? (
            <>
              <span className="w-2 h-2 rounded-full bg-accent animate-pulse" />
              {statusMessage}
            </>
          ) : (
            <>
              <span className="w-2 h-2 rounded-full bg-success" />
              {statusMessage}
            </>
          )}
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 min-h-0 overflow-y-auto">
        {messages.map((msg, i) => (
          <MessageBubble
            key={i}
            role={msg.role}
            content={msg.content}
            agent={msg.agent}
            isStreaming={isStreaming && i === messages.length - 1 && msg.role === "assistant"}
          />
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
