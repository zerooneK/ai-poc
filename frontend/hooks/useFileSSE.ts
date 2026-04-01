"use client";

import { useState, useEffect, useCallback, useRef } from "react";

const API_BASE =
  typeof process !== "undefined"
    ? process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000"
    : "http://localhost:5000";

export function useFileSSE() {
  const [fileChanged, setFileChanged] = useState(0);
  const abortRef = useRef<AbortController | null>(null);

  const connect = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort();
    }

    const controller = new AbortController();
    abortRef.current = controller;

    const connectStream = async () => {
      try {
        const response = await fetch(`${API_BASE}/api/files/stream`, {
          signal: controller.signal,
        });

        if (!response.ok) return;

        const reader = response.body?.getReader();
        if (!reader) return;

        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const chunks = buffer.split("\n\n");
          buffer = chunks.pop() || "";

          for (const chunk of chunks) {
            const dataLine = chunk
              .split("\n")
              .find((line) => line.startsWith("data: "));
            if (!dataLine) continue;

            try {
              const event = JSON.parse(dataLine.slice(6));
              if (event.type === "files_changed") {
                setFileChanged((n) => n + 1);
              }
            } catch {
              // Skip malformed
            }
          }
        }
      } catch {
        // Reconnect after 2s if not aborted
        if (!controller.signal.aborted) {
          setTimeout(connectStream, 2000);
        }
      }
    };

    connectStream();
  }, []);

  useEffect(() => {
    connect();
    return () => {
      if (abortRef.current) {
        abortRef.current.abort();
      }
    };
  }, [connect]);

  return { fileChanged, reconnect: connect };
}
