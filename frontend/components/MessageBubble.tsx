"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { cn, agentLabel, agentIcon } from "@/lib/utils";

interface MessageBubbleProps {
  role: "user" | "assistant";
  content: string;
  agent?: string;
  isStreaming?: boolean;
}

export default function MessageBubble({
  role,
  content,
  agent,
  isStreaming = false,
}: MessageBubbleProps) {
  const isUser = role === "user";

  return (
    <div
      className={cn(
        "mx-auto flex max-w-4xl gap-3 px-4 py-3",
        isUser ? "justify-end" : "justify-start"
      )}
    >
      {!isUser && (
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-2xl border border-border bg-surface-elevated text-sm shadow-sm">
          {agent ? agentIcon(agent) : "🤖"}
        </div>
      )}

      <div
        className={cn(
          "max-w-[80%] rounded-[22px] border px-4 py-3 text-sm leading-relaxed shadow-[0_10px_30px_rgba(15,23,42,0.08)]",
          isUser
            ? "border-transparent bg-accent text-white"
            : "border-border bg-surface-elevated text-text-primary"
        )}
      >
        {!isUser && agent && (
          <div className="mb-2 flex items-center gap-1.5 border-b border-border-light pb-2">
            <span className="text-xs font-medium uppercase tracking-[0.14em] text-text-secondary">
              {agentIcon(agent)} {agentLabel(agent)}
            </span>
          </div>
        )}

        {isUser ? (
          <p className="whitespace-pre-wrap">{content}</p>
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
