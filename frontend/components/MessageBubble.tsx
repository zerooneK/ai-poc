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
        "flex gap-3 px-4 py-3 max-w-4xl mx-auto",
        isUser ? "justify-end" : "justify-start"
      )}
    >
      {!isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-bg-tertiary flex items-center justify-center text-sm">
          {agent ? agentIcon(agent) : "🤖"}
        </div>
      )}

      <div
        className={cn(
          "rounded-lg px-4 py-3 max-w-[80%] text-sm leading-relaxed",
          isUser
            ? "bg-accent text-white"
            : "bg-bg-tertiary text-text-primary"
        )}
      >
        {!isUser && agent && (
          <div className="flex items-center gap-1.5 mb-2 pb-2 border-b border-border-light">
            <span className="text-xs font-medium text-text-secondary">
              {agentIcon(agent)} {agentLabel(agent)}
            </span>
          </div>
        )}

        {isUser ? (
          <p className="whitespace-pre-wrap">{content}</p>
        ) : (
          <div
            className="prose prose-invert prose-sm max-w-none
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
          <span className="inline-block w-2 h-4 bg-text-secondary animate-pulse ml-1" />
        )}
      </div>
    </div>
  );
}
