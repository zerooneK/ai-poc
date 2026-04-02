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
  isLoadingSession?: boolean;
}

const QUICK_ACTIONS = [
  { label: "สร้างเอกสาร HR", icon: "👤", prompt: "ช่วยสร้างเอกสาร HR ให้หน่อย" },
  { label: "สร้างรายงานการเงิน", icon: "💰", prompt: "ช่วยสร้างรายงานการเงินให้หน่อย" },
  { label: "คำแนะนำการจัดการ", icon: "📋", prompt: "ช่วยให้คำแนะนำด้านการจัดการทีม" },
  { label: "สนทนาทั่วไป", icon: "💬", prompt: "มาคุยกันทั่วไป" },
];

export default function ChatWindow({
  messages,
  isStreaming,
  statusMessage,
  hasError,
  errorMessage,
  isEmpty,
  onQuickAction,
  isLoadingSession = false,
}: ChatWindowProps) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const userScrolledUpRef = useRef(false);
  const programmaticScrollRef = useRef(false);

  // Detect user-initiated scrolls (ignore programmatic ones)
  useEffect(() => {
    const container = scrollContainerRef.current;
    if (!container) return;
    const handleScroll = () => {
      if (programmaticScrollRef.current) return;
      const threshold = 80;
      const atBottom =
        container.scrollTop + container.clientHeight >=
        container.scrollHeight - threshold;
      userScrolledUpRef.current = !atBottom;
    };
    container.addEventListener("scroll", handleScroll, { passive: true });
    return () => container.removeEventListener("scroll", handleScroll);
  }, []);

  // Reset scroll lock when user sends a new message
  useEffect(() => {
    if (messages.length > 0 && messages[messages.length - 1].role === "user") {
      userScrolledUpRef.current = false;
    }
  }, [messages.length]);

  // Auto-scroll only when user hasn't scrolled up
  useEffect(() => {
    if (userScrolledUpRef.current) return;
    programmaticScrollRef.current = true;
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    requestAnimationFrame(() => {
      programmaticScrollRef.current = false;
    });
  }, [messages, statusMessage]);

  if (isLoadingSession) {
    return (
      <div className="flex h-full items-center justify-center px-4 text-center">
        <div className="rounded-[28px] border border-border bg-surface px-8 py-10 shadow-[0_20px_60px_rgba(15,23,42,0.1)] backdrop-blur-xl">
          <div className="mx-auto mb-3 h-8 w-8 animate-spin rounded-full border-2 border-border border-t-accent" />
          <p className="text-sm font-medium text-text-primary">
            กำลังโหลดเซสชัน...
          </p>
          <p className="mt-1 text-xs text-text-muted">
            กำลังกู้คืนประวัติแชทและข้อมูล workspace
          </p>
        </div>
      </div>
    );
  }

  if (isEmpty) {
    return (
      <div className="flex h-full items-center justify-center px-4 py-6">
        <div className="w-full max-w-2xl rounded-[30px] border border-border bg-surface px-6 py-8 text-center shadow-[0_20px_60px_rgba(15,23,42,0.08)] backdrop-blur-xl sm:px-8">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-[22px] bg-bg-tertiary text-4xl shadow-inner">
            🤖
          </div>
          <h2 className="mb-2 text-2xl font-semibold tracking-tight text-text-primary">
            สวัสดี มีอะไรให้ช่วยไหม?
          </h2>
          <p className="mx-auto max-w-lg text-sm leading-6 text-text-secondary">
            พิมพ์ข้อความเพื่อเริ่มใช้งาน หรือเลือกแนวทางด้านล่าง ระบบจะเลือก agent
            ที่เหมาะสมให้อัตโนมัติ
          </p>
          <div className="mt-6 grid grid-cols-1 gap-3 text-left sm:grid-cols-2">
          {QUICK_ACTIONS.map((action) => (
            <button
              key={action.label}
              onClick={() => onQuickAction(action.prompt)}
              className="group rounded-[20px] border border-border bg-bg-secondary/70 px-4 py-3 transition-all hover:-translate-y-0.5 hover:border-accent/40 hover:bg-bg-hover/80"
              type="button"
            >
              <div className="flex items-start gap-3">
                <span className="mt-0.5 flex h-9 w-9 items-center justify-center rounded-xl bg-bg-tertiary text-base">
                  {action.icon}
                </span>
                <div>
                  <p className="text-sm font-medium text-text-primary">
                    {action.label}
                  </p>
                  <p className="mt-1 text-xs leading-4 text-text-secondary">
                    เปิดบทสนทนาด้วยคำสั่งตัวอย่างที่เหมาะกับงานนี้
                  </p>
                </div>
              </div>
            </button>
          ))}
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
            "mx-4 mt-4 flex shrink-0 items-center gap-2 rounded-2xl border px-4 py-3 text-xs shadow-sm",
            hasError
              ? "border-error/30 bg-error/10 text-error"
              : "border-border bg-surface text-text-secondary"
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
      <div ref={scrollContainerRef} className="flex-1 min-h-0 overflow-y-auto pt-4">
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
