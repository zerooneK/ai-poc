import { useState, useCallback, useRef } from "react";

// ─── Types ───────────────────────────────────────────────────────────

export interface SSEEvent {
  type: string;
  [key: string]: unknown;
}

export interface UseSSEReturn {
  /** Accumulated output text from the stream */
  outputText: string;
  /** Current status message (e.g. "กำลังวิเคราะห์งาน...") */
  statusMessage: string;
  /** Whether a stream is currently active */
  isStreaming: boolean;
  /** Whether the last stream ended in an error */
  hasError: boolean;
  /** Error message if hasError is true */
  errorMessage: string | null;
  /** The last SSE event received (for type-specific handling) */
  lastEvent: SSEEvent | null;
  /** PM plan subtasks (if PM agent was routed) */
  pmPlan: Array<{ agent: string; task: string }> | null;
  /** Send a message to start a new SSE stream */
  sendMessage: (message: string, options?: SendMessageOptions) => void;
  /** Abort the current stream */
  abort: () => void;
}

export interface StreamCompletePayload {
  outputText: string;
  agent?: string;
}

export type OnStreamComplete = (payload: StreamCompletePayload) => void;

export interface SendMessageOptions {
  conversationHistory?: Array<{ role: string; content: string }>;
  sessionId?: string;
  pendingDoc?: string;
  pendingAgent?: string;
  pendingTempPaths?: string[];
  agentTypes?: string[];
  outputFormat?: string;
  outputFormats?: string[];
  overwriteFilename?: string;
  localAgentMode?: boolean;
  onStreamComplete?: OnStreamComplete;
}

// ─── Fake tool-call regex (strips LLM hallucinated tool JSON) ────────

const FAKE_TOOL_CALL_RE =
  /\{"(?:request|tool_call|tool)":\s*"[^"]*"[^}]*\}/g;

function stripFakeToolCalls(text: string): string {
  return text.replace(FAKE_TOOL_CALL_RE, "").trim();
}

// ─── Hook ────────────────────────────────────────────────────────────

const API_BASE =
  typeof process !== "undefined"
    ? process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000"
    : "http://localhost:5000";

export function useSSE(): UseSSEReturn {
  const [outputText, setOutputText] = useState("");
  const [statusMessage, setStatusMessage] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [hasError, setHasError] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [lastEvent, setLastEvent] = useState<SSEEvent | null>(null);
  const [pmPlan, setPmPlan] = useState<
    Array<{ agent: string; task: string }> | null
  >(null);

  const abortRef = useRef<AbortController | null>(null);
  const outputRef = useRef("");
  const optionsRef = useRef<SendMessageOptions | undefined>(undefined);
  const lastEventRef = useRef<SSEEvent | null>(null);
  const lastAgentRef = useRef<string | undefined>(undefined);
  const streamCompletedRef = useRef(false);

  const finalizeStream = useCallback(() => {
    if (streamCompletedRef.current) return;
    streamCompletedRef.current = true;
    setIsStreaming(false);
    if (optionsRef.current?.onStreamComplete) {
      optionsRef.current.onStreamComplete({
        outputText: stripFakeToolCalls(outputRef.current),
        agent: lastAgentRef.current,
      });
    }
  }, []);

  const abort = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
    setIsStreaming(false);
  }, []);

  const sendMessage = useCallback(
    (message: string, options?: SendMessageOptions) => {
      optionsRef.current = options;
      // Reset state
      outputRef.current = "";
      setOutputText("");
      setStatusMessage("");
      setHasError(false);
      setErrorMessage(null);
      setLastEvent(null);
      setPmPlan(null);
      setIsStreaming(true);
      lastAgentRef.current = undefined;
      streamCompletedRef.current = false;

      const controller = new AbortController();
      abortRef.current = controller;

      const body = {
        message,
        conversation_history: options?.conversationHistory,
        session_id: options?.sessionId,
        pending_doc: options?.pendingDoc,
        pending_agent: options?.pendingAgent,
        pending_temp_paths: options?.pendingTempPaths,
        agent_types: options?.agentTypes,
        output_format: options?.outputFormat,
        output_formats: options?.outputFormats,
        overwrite_filename: options?.overwriteFilename,
        local_agent_mode: options?.localAgentMode,
      };

      fetch(`${API_BASE}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
        signal: controller.signal,
      })
        .then(async (response) => {
          if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
          }

          const reader = response.body?.getReader();
          if (!reader) throw new Error("No response body");

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

              let event: SSEEvent;
              try {
                event = JSON.parse(dataLine.slice(6));
              } catch {
                continue;
              }

              setLastEvent(event);
              lastEventRef.current = event;

              switch (event.type) {
                case "status":
                  setStatusMessage(event.message as string);
                  break;

                case "agent":
                  lastAgentRef.current = event.agent as string | undefined;
                  setStatusMessage(
                    event.reason
                      ? `${event.agent} — ${event.reason}`
                      : (event.agent as string)
                  );
                  break;

                case "pm_plan":
                  setPmPlan(event.subtasks as Array<{ agent: string; task: string }>);
                  break;

                case "text":
                  outputRef.current += event.content as string;
                  setOutputText(
                    stripFakeToolCalls(outputRef.current)
                  );
                  break;

                case "tool_result":
                  // Tool results are shown inline by the UI
                  break;

                case "pending_file":
                  // File was written — UI can track it
                  break;

                case "subtask_done":
                  // PM subtask completed
                  break;

                case "local_delete":
                  // Local agent deleted a file
                  break;

                case "delete_request":
                  // Agent wants to delete a file — UI shows confirm
                  break;

                case "save_failed":
                  setHasError(true);
                  setErrorMessage(event.message as string);
                  break;

                case "error":
                  setHasError(true);
                  setErrorMessage(event.message as string);
                  break;

                case "done":
                  finalizeStream();
                  break;
              }
            }
          }

          // Stream ended without explicit "done" event
          finalizeStream();
        })
        .catch((err) => {
          if (err.name !== "AbortError") {
            setHasError(true);
            setErrorMessage(err.message || "เกิดข้อผิดพลาดในการเชื่อมต่อ");
            setIsStreaming(false);
          }
        });
    },
    [finalizeStream]
  );

  return {
    outputText,
    statusMessage,
    isStreaming,
    hasError,
    errorMessage,
    lastEvent,
    pmPlan,
    sendMessage,
    abort,
  };
}
