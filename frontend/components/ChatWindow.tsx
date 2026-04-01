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
}

export default function ChatWindow({
  messages,
  isStreaming,
  statusMessage,
  hasError,
  errorMessage,
  isEmpty,
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
          <div className="bg-bg-tertiary rounded-lg px-4 py-3">
            👤 สร้างเอกสาร HR
          </div>
          <div className="bg-bg-tertiary rounded-lg px-4 py-3">
            💰 สร้างรายงานการเงิน
          </div>
          <div className="bg-bg-tertiary rounded-lg px-4 py-3">
            📋 คำแนะนำการจัดการ
          </div>
          <div className="bg-bg-tertiary rounded-lg px-4 py-3">
            💬 สนทนาทั่วไป
          </div>
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
      <div className="flex-1 overflow-y-auto">
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
