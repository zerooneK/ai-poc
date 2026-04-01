"use client";

import { useState, useCallback } from "react";
import { useSSE } from "@/hooks/useSSE";
import ChatWindow from "@/components/ChatWindow";
import InputArea from "@/components/InputArea";

interface Message {
  role: "user" | "assistant";
  content: string;
  agent?: string;
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [conversationHistory, setConversationHistory] = useState<
    Array<{ role: string; content: string }>
  >([]);

  const {
    statusMessage,
    isStreaming,
    hasError,
    errorMessage,
    sendMessage,
  } = useSSE();

  const handleStreamComplete = useCallback(
    (payload: { outputText: string; agent?: string }) => {
      const assistantMsg: Message = {
        role: "assistant",
        content: payload.outputText,
        agent: payload.agent,
      };
      setMessages((prev) => [...prev, assistantMsg]);
      setConversationHistory((prev) => [
        ...prev,
        { role: "assistant", content: payload.outputText },
      ]);
    },
    []
  );

  const handleSend = useCallback(
    (text: string) => {
      const userMsg: Message = { role: "user", content: text };
      setMessages((prev) => [...prev, userMsg]);
      setConversationHistory((prev) => [
        ...prev,
        { role: "user", content: text },
      ]);

      sendMessage(text, {
        conversationHistory,
        onStreamComplete: handleStreamComplete,
      });
    },
    [conversationHistory, sendMessage, handleStreamComplete]
  );

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-hidden">
        <ChatWindow
          messages={messages}
          isStreaming={isStreaming}
          statusMessage={statusMessage}
          hasError={hasError}
          errorMessage={errorMessage}
          isEmpty={messages.length === 0}
        />
      </div>
      <InputArea onSend={handleSend} isStreaming={isStreaming} />
    </div>
  );
}
