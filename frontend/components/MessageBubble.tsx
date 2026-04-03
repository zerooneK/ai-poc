"use client";

import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { cn, agentLabel, agentIcon } from "@/lib/utils";
import type { ToolEvent } from "@/hooks/useSSE";

// ─── Tool icon/label helpers ────────────────────────────────────────

const TOOL_ICONS: Record<string, string> = {
  read_file: "📖",
  create_file: "📝",
  write_file: "✏️",
  list_files: "📂",
  delete_file: "🗑️",
  search_files: "🔍",
  web_search: "🌐",
};

const TOOL_LABELS: Record<string, string> = {
  read_file: "อ่านไฟล์",
  create_file: "สร้างไฟล์",
  write_file: "เขียนไฟล์",
  list_files: "ดูรายการไฟล์",
  delete_file: "ลบไฟล์",
  search_files: "ค้นหาไฟล์",
  web_search: "ค้นหาเว็บ",
};

function toolIcon(tool: string): string {
  return TOOL_ICONS[tool] ?? "🔧";
}

function toolLabel(tool: string): string {
  return TOOL_LABELS[tool] ?? tool;
}

// ─── ToolResultRow ───────────────────────────────────────────────────

function ToolResultRow({ event }: { event: ToolEvent }) {
  const tool = event.tool ?? "unknown";
  return (
    <div className="flex items-center gap-2 text-xs text-text-secondary">
      <span className="shrink-0 text-sm opacity-70">{toolIcon(tool)}</span>
      <span className="font-medium">{toolLabel(tool)}</span>
      {event.filename && (
        <>
          <span className="opacity-40">·</span>
          <span className="truncate font-mono text-text-muted">{event.filename}</span>
        </>
      )}
      {event.success === false && (
        <span className="ml-auto shrink-0 text-[10px] text-error opacity-80">
          ล้มเหลว
        </span>
      )}
    </div>
  );
}

// ─── WebSearchRow ────────────────────────────────────────────────────

function WebSearchRow({ event }: { event: ToolEvent }) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-center gap-2 text-xs text-text-secondary">
        <span className="shrink-0 text-sm opacity-70">🔍</span>
        <span className="font-medium">ค้นหา</span>
        {event.query && (
          <>
            <span className="opacity-40">·</span>
            <span className="italic opacity-70">&ldquo;{event.query}&rdquo;</span>
          </>
        )}
      </div>
      {event.sources && event.sources.length > 0 && (
        <div className="flex flex-wrap gap-1.5 pl-6">
          {event.sources.slice(0, 5).map((src, i) => (
            <a
              key={i}
              href={src.url}
              target="_blank"
              rel="noopener noreferrer"
              title={src.snippet ?? src.title}
              className="inline-flex max-w-[160px] items-center truncate rounded-full border border-border bg-bg-primary/50 px-2.5 py-0.5 text-[11px] text-text-secondary transition-colors hover:border-accent/40 hover:text-text-primary"
            >
              {src.title}
            </a>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── ActionLog ───────────────────────────────────────────────────────

function ActionLog({ toolEvents }: { toolEvents: ToolEvent[] }) {
  if (toolEvents.length === 0) return null;
  return (
    <div className="mb-3 rounded-[16px] bg-bg-tertiary px-3 py-2.5">
      <p className="mb-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-text-muted">
        AI ดำเนินการ
      </p>
      <div className="max-h-32 space-y-2 overflow-y-auto">
        {toolEvents.map((ev, i) =>
          ev.type === "web_search_sources" ? (
            <WebSearchRow key={i} event={ev} />
          ) : (
            <ToolResultRow key={i} event={ev} />
          )
        )}
      </div>
    </div>
  );
}

export default React.memo(MessageBubble);

// ─── MessageBubble ───────────────────────────────────────────────────

interface MessageBubbleProps {
  role: "user" | "assistant";
  content: string;
  agent?: string;
  isStreaming?: boolean;
  toolEvents?: ToolEvent[];
}

function MessageBubble({
  role,
  content,
  agent,
  isStreaming = false,
  toolEvents,
}: MessageBubbleProps) {
  const isUser = role === "user";

  return (
    <div
      className={cn(
        "flex gap-3 px-5 py-3",
        isUser ? "justify-end" : "justify-start"
      )}
    >
      {!isUser && (
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[16px] bg-surface text-sm shadow-ambient">
          {agent ? agentIcon(agent) : "🤖"}
        </div>
      )}

      <div
        className={cn(
          "rounded-[24px] px-4 py-3 text-[15px] leading-relaxed shadow-ambient relative overflow-hidden",
          isUser
            ? "max-w-[80%] bg-bg-tertiary text-text-primary"
            : "w-full bg-surface text-text-primary"
        )}
      >
        {!isUser && (
          <div className="absolute left-0 top-0 bottom-0 w-1 bg-accent" />
        )}
        {!isUser && agent && (
          <div className="mb-2 flex items-center gap-1.5 pb-2">
            <span className="text-xs font-medium uppercase tracking-[0.14em] text-text-secondary">
              {agentIcon(agent)} {agentLabel(agent)}
            </span>
          </div>
        )}

        {!isUser && toolEvents && toolEvents.length > 0 && (
          <ActionLog toolEvents={toolEvents} />
        )}

        {isUser ? (
          <p className="whitespace-pre-wrap break-words">{content}</p>
        ) : (
          <div
            className="prose prose-sm max-w-none
              prose-headings:text-text-primary
              prose-p:text-text-primary
              prose-code:text-accent
              prose-pre:bg-bg-primary
              prose-pre:border prose-pre:border-border
              prose-strong:text-text-primary
              prose-a:text-text-link
              prose-li:text-text-primary
              prose-table:text-text-primary
              prose-th:border prose-th:border-border
              prose-td:border prose-td:border-border"
          >
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {content}
            </ReactMarkdown>
          </div>
        )}

        {isStreaming && !isUser && (
          <span className="ml-1 inline-block h-4 w-2 animate-pulse rounded-full bg-text-secondary" />
        )}
      </div>
    </div>
  );
}
