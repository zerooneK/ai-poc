"use client";

import { useState, useCallback, useEffect, useMemo, useRef } from "react";
import { useSSE, type ToolEvent } from "@/hooks/useSSE";
import { useFileSSE } from "@/hooks/useFileSSE";
import { useSessions } from "@/hooks/useSessions";
import { useShortcuts } from "@/lib/shortcuts";
import ChatWindow from "@/components/ChatWindow";
import InputArea from "@/components/InputArea";
import PreviewPanel from "@/components/PreviewPanel";
import WorkspaceModal from "@/components/WorkspaceModal";
import FormatModal from "@/components/FormatModal";
import DeleteConfirmModal from "@/components/DeleteConfirmModal";
import ErrorBoundary from "@/components/ErrorBoundary";
import {
  deleteSession,
  deleteFileForSession,
  getFilesForSession,
  getWorkspaceForSession,
} from "@/lib/api";
import { fileIcon, formatBytes, agentLabel } from "@/lib/utils";

interface Message {
  role: "user" | "assistant";
  content: string;
  agent?: string;
  toolEvents?: ToolEvent[];
}

interface WorkspaceFile {
  name: string;
  size: number;
  modified: string;
}

function createSessionId(): string {
  return typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
    ? crypto.randomUUID()
    : `session-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function getSessionBadgeLabel(firstMessage: string): string {
  const trimmed = firstMessage.trim();
  const firstChar = trimmed.charAt(0);
  if (!firstChar) return "•";
  if (/[A-Za-z0-9]/.test(firstChar)) {
    return firstChar.toUpperCase();
  }
  return firstChar;
}

type ThemeMode = "light" | "dark";

const SAVE_INTENT_RE = /^(save|ok|บันทึก|เซฟ|ตกลง|ได้เลย|โอเค)$/i;

function isSaveIntent(text: string): boolean {
  return SAVE_INTENT_RE.test(text.trim());
}

export default function Home() {
  const [sessionId, setSessionId] = useState(() => {
    if (typeof window === "undefined") return "";
    const id = createSessionId();
    return id;
  });
  const [selectedSessionId, setSelectedSessionId] = useState(() => sessionId);
  const [messages, setMessages] = useState<Message[]>([]);
  const [conversationHistory, setConversationHistory] = useState<
    Array<{ role: string; content: string }>
  >([]);
  const [workspacePath, setWorkspacePath] = useState("");
  const [files, setFiles] = useState<WorkspaceFile[]>([]);
  const [workspaceModalOpen, setWorkspaceModalOpen] = useState(false);
  const [previewFile, setPreviewFile] = useState<string | null>(null);
  const [formatModalOpen, setFormatModalOpen] = useState(false);
  const [pendingFilename, setPendingFilename] = useState("");
  const [pendingAgentLabel, setPendingAgentLabel] = useState("");
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [deleteFilename, setDeleteFilename] = useState("");
  const [isSwitchingSession, setIsSwitchingSession] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [theme, setTheme] = useState<ThemeMode>("dark");
  const [pendingDoc, setPendingDoc] = useState("");
  const [pendingAgent, setPendingAgent] = useState("");
  const [pendingTempPaths, setPendingTempPaths] = useState<string[]>([]);
  const [pendingAgentTypes, setPendingAgentTypes] = useState<string[]>([]);
  const sessionCacheRef = useRef<
    Map<string, {
      messages: Message[];
      history: Array<{ role: string; content: string }>;
    }>
  >(new Map());
  const saveRequestRef = useRef(false);

  const {
    outputText,
    statusMessage,
    isStreaming,
    hasError,
    errorMessage,
    lastEvent,
    pendingFiles,
    currentToolEvents,
    sendMessage,
  } = useSSE();

  const { fileChanged, reconnect: reconnectFileSSE } = useFileSSE(sessionId);
  const { sessions, loadSessions, loadSessionJobs } = useSessions();

  // Load session workspace on mount
  useEffect(() => {
    if (!sessionId) return;
    getWorkspaceForSession(sessionId)
      .then((res) => setWorkspacePath(res.workspace))
      .catch(() => {});
  }, [sessionId]);

  // Load files on mount and when fileChanged updates
  useEffect(() => {
    if (!sessionId) return;
    getFilesForSession(sessionId)
      .then((res) => setFiles(res.files))
      .catch(() => {});
  }, [fileChanged, sessionId]);

  // Load sessions on mount
  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  useEffect(() => {
    const root = document.documentElement;
    const currentTheme = root.dataset.theme === "light" ? "light" : "dark";
    setTheme(currentTheme);
  }, []);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    window.localStorage.setItem("ai-poc-theme", theme);
  }, [theme]);

  const handleSessionSelect = useCallback(
    async (selectedSessionId: string) => {
      if (!selectedSessionId) return;
      const shouldReloadCurrentSession =
        selectedSessionId === sessionId &&
        messages.length === 0 &&
        conversationHistory.length === 0;

      if (selectedSessionId === sessionId && !shouldReloadCurrentSession) {
        return;
      }
      setSelectedSessionId(selectedSessionId);
      setPreviewFile(null);
      setPendingDoc("");
      setPendingAgent("");
      setPendingTempPaths([]);
      setPendingAgentTypes([]);
      setPendingFilename("");
      setPendingAgentLabel("");
      setSessionId(selectedSessionId);
      const cachedSession = sessionCacheRef.current.get(selectedSessionId);
      if (
        cachedSession &&
        (cachedSession.messages.length > 0 || cachedSession.history.length > 0)
      ) {
        setMessages(cachedSession.messages);
        setConversationHistory(cachedSession.history);
        return;
      }

      setIsSwitchingSession(true);
      setMessages([]);
      setConversationHistory([]);

      try {
        const response = await loadSessionJobs(selectedSessionId);
        const restoredMessages: Message[] = [];
        const restoredHistory: Array<{ role: string; content: string }> = [];

        for (const job of response.jobs) {
          if (job.user_input) {
            restoredMessages.push({ role: "user", content: job.user_input });
            restoredHistory.push({ role: "user", content: job.user_input });
          }
          if (job.output_text) {
            restoredMessages.push({
              role: "assistant",
              content: job.output_text,
              agent: job.agent || undefined,
            });
            restoredHistory.push({ role: "assistant", content: job.output_text });
          }
        }

        sessionCacheRef.current.set(selectedSessionId, {
          messages: restoredMessages,
          history: restoredHistory,
        });
        setMessages(restoredMessages);
        setConversationHistory(restoredHistory);
      } finally {
        setIsSwitchingSession(false);
      }
    },
    [conversationHistory.length, loadSessionJobs, messages.length, sessionId]
  );

  // Always-current ref so onStreamComplete (stored in useSSE's optionsRef at sendMessage time)
  // never calls a stale closure — avoids hasError / pendingFiles staleness bugs.
  const hasErrorRef = useRef(hasError);
  hasErrorRef.current = hasError;

  const handleStreamComplete = useCallback(
    (outputText: string, agent?: string, toolEvents?: ToolEvent[]) => {
      if (outputText.trim()) {
        const assistantMsg: Message = {
          role: "assistant",
          content: outputText,
          agent,
          toolEvents,
        };
        setMessages((prev) => [...prev, assistantMsg]);
        setConversationHistory((prev) => [
          ...prev,
          { role: "assistant", content: outputText },
        ]);
      }
      if (saveRequestRef.current) {
        saveRequestRef.current = false;
        if (!hasErrorRef.current) {
          setPendingDoc("");
          setPendingAgent("");
          setPendingTempPaths([]);
          setPendingAgentTypes([]);
          setPendingFilename("");
          setPendingAgentLabel("");
          getFilesForSession(sessionId)
            .then((res) => setFiles(res.files))
            .catch(() => {});
        }
      } else if (pendingFiles.length > 0) {
        setPendingDoc("");
        setPendingAgent("");
        setPendingTempPaths(pendingFiles.map((file) => file.tempPath).filter(Boolean));
        setPendingAgentTypes(pendingFiles.map((file) => file.agent || "").filter(Boolean));
        setPendingFilename(pendingFiles.map((file) => file.filename).filter(Boolean).join(", "));
        setPendingAgentLabel("หลาย agent");
      } else if (outputText.trim()) {
        setPendingDoc(outputText);
        setPendingAgent(agent || "");
        setPendingTempPaths([]);
        setPendingAgentTypes([]);
        setPendingFilename("เอกสารใหม่");
        setPendingAgentLabel(agent ? agentLabel(agent) : "Assistant");
      }
      loadSessions();
    },
    [loadSessions, pendingFiles, sessionId]
  );

  // Ref keeps onStreamComplete always calling the latest handleStreamComplete,
  // even though useSSE captures options at sendMessage call time.
  const handleStreamCompleteRef = useRef(handleStreamComplete);
  handleStreamCompleteRef.current = handleStreamComplete;

  const submitMessage = useCallback(
    (
      text: string,
      options?: {
        outputFormat?: string;
        forcePendingState?: boolean;
      }
    ) => {
      const userMsg: Message = { role: "user", content: text };
      setMessages((prev) => [...prev, userMsg]);
      setConversationHistory((prev) => [
        ...prev,
        { role: "user", content: text },
      ]);

      const shouldSendPendingState =
        options?.forcePendingState ||
        Boolean(pendingDoc || pendingTempPaths.length > 0);

      sendMessage(text, {
        conversationHistory,
        sessionId,
        pendingDoc: shouldSendPendingState ? pendingDoc : undefined,
        pendingAgent: shouldSendPendingState ? pendingAgent : undefined,
        pendingTempPaths: shouldSendPendingState ? pendingTempPaths : undefined,
        agentTypes: shouldSendPendingState ? pendingAgentTypes : undefined,
        outputFormat: options?.outputFormat,
        onStreamComplete: (payload) => {
          handleStreamCompleteRef.current(payload.outputText, payload.agent, payload.toolEvents);
        },
      });
      loadSessions();
    },
    [
      conversationHistory,
      loadSessions,
      pendingAgent,
      pendingAgentTypes,
      pendingDoc,
      pendingTempPaths,
      sendMessage,
      sessionId,
    ]
  );

  const handleSend = useCallback(
    (text: string) => {
      if ((pendingDoc || pendingTempPaths.length > 0) && isSaveIntent(text)) {
        setFormatModalOpen(true);
        return;
      }
      submitMessage(text);
    },
    [pendingDoc, pendingTempPaths.length, submitMessage]
  );

  const handleWorkspaceSwitch = (path: string) => {
    setWorkspacePath(path);
    setFiles([]);
    setConversationHistory([]);
    setMessages([]);
    setPendingDoc("");
    setPendingAgent("");
    setPendingTempPaths([]);
    setPendingAgentTypes([]);
    setPendingFilename("");
    setPendingAgentLabel("");
    // Reconnect SSE so it watches the new workspace directory
    reconnectFileSSE();
  };

  const handleDeleteFile = (filename: string) => {
    setDeleteFilename(filename);
    setDeleteModalOpen(true);
  };

  const handleDeleteSession = useCallback(
    async (targetSessionId: string) => {
      if (!window.confirm("ลบเซสชันนี้และประวัติแชททั้งหมดใช่หรือไม่?")) {
        return;
      }

      await deleteSession(targetSessionId);
      setPreviewFile(null);

      if (targetSessionId === sessionId) {
        setMessages([]);
        setConversationHistory([]);
        setSelectedSessionId("");
        setPendingDoc("");
        setPendingAgent("");
        setPendingTempPaths([]);
        setPendingAgentTypes([]);
        setPendingFilename("");
        setPendingAgentLabel("");
      }

      sessionCacheRef.current.delete(targetSessionId);
      loadSessions();
    },
    [loadSessions, sessionId]
  );

  const handleNewSession = useCallback(() => {
    const nextSessionId = createSessionId();
    setPreviewFile(null);
    setMessages([]);
    setConversationHistory([]);
    setFiles([]);
    setPendingDoc("");
    setPendingAgent("");
    setPendingTempPaths([]);
    setPendingAgentTypes([]);
    setPendingFilename("");
    setPendingAgentLabel("");
    setSessionId(nextSessionId);
    setSelectedSessionId(nextSessionId);
    setIsSwitchingSession(false);
  }, []);

  const toggleTheme = useCallback(() => {
    setTheme((prev) => (prev === "dark" ? "light" : "dark"));
  }, []);

  const toggleSidebar = useCallback(() => {
    setSidebarCollapsed((prev) => !prev);
  }, []);

  const confirmDelete = () => {
    deleteFileForSession(deleteFilename, sessionId)
      .then(() => {
        setDeleteModalOpen(false);
        getFilesForSession(sessionId)
          .then((res) => setFiles(res.files))
          .catch(() => {});
      })
      .catch(() => {});
  };

  useShortcuts({
    onClosePanel: previewFile ? () => setPreviewFile(null) : undefined,
    onOpenWorkspace: () => setWorkspaceModalOpen(true),
  });

  useEffect(() => {
    if (!sessionId) return;
    const existing = sessionCacheRef.current.get(sessionId);
    const hasVisibleContent = messages.length > 0 || conversationHistory.length > 0;

    if (hasVisibleContent || !existing) {
      sessionCacheRef.current.set(sessionId, {
        messages,
        history: conversationHistory,
      });
    }
  }, [conversationHistory, messages, sessionId]);

  useEffect(() => {
    if (lastEvent?.type === "save_failed") {
      saveRequestRef.current = false;
    }
  }, [lastEvent]);

  useEffect(() => {
    if (pendingFiles.length === 0) return;
    setPendingTempPaths(pendingFiles.map((file) => file.tempPath).filter(Boolean));
    setPendingAgentTypes(pendingFiles.map((file) => file.agent || "").filter(Boolean));
    setPendingFilename(pendingFiles.map((file) => file.filename).filter(Boolean).join(", "));
    setPendingAgentLabel("หลาย agent");
  }, [pendingFiles]);

  const visibleMessages = useMemo(() => {
    if (!isStreaming || !outputText.trim()) {
      return messages;
    }

    return [
      ...messages,
      {
        role: "assistant" as const,
        content: outputText,
        toolEvents: currentToolEvents.length > 0 ? currentToolEvents : undefined,
      },
    ];
  }, [isStreaming, messages, outputText, currentToolEvents]);

  return (
    <ErrorBoundary>
      <div className="app-shell relative flex h-full flex-col">
        <header className="shrink-0 bg-bg-secondary/80 px-4 backdrop-blur-xl">
          <div className="mx-auto flex h-16 max-w-[1600px] items-center justify-between gap-4">
            <div className="min-w-0">
              <p className="text-sm font-semibold tracking-tight text-text-primary">
                AI Workspace Assistant
              </p>
              <p className="truncate text-xs text-text-muted">
                พื้นที่ทำงานสนทนาแบบสะอาดตา พร้อมสลับธีมและจัดการเซสชันได้ทันที
              </p>
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={toggleTheme}
                className="flex h-10 items-center gap-2 rounded-full border border-border bg-surface px-3 pr-2 text-sm text-text-secondary transition-colors hover:bg-bg-hover"
                aria-label="สลับธีม"
              >
                <span className="text-sm">{theme === "dark" ? "🌙" : "☀️"}</span>
                <span className="hidden sm:inline">
                  {theme === "dark" ? "Dark" : "Light"}
                </span>
                <span className="relative block h-5 w-10 rounded-full bg-bg-tertiary">
                  <span
                    className={`absolute left-0.5 top-0.5 h-4 w-4 rounded-full bg-accent transition-transform ${
                      theme === "dark" ? "translate-x-5" : "translate-x-0"
                    }`}
                  />
                </span>
              </button>
              <button
                onClick={handleNewSession}
                className="h-10 rounded-full bg-accent px-3 text-sm font-medium text-white transition-all hover:bg-accent-hover hover:shadow-[0_12px_28px_rgba(45,108,223,0.3)]"
              >
                สร้างเซสชันใหม่
              </button>
            </div>
          </div>
        </header>
        <div className="mx-auto flex min-h-0 w-full max-w-[1600px] flex-1 overflow-hidden px-3 pb-3 pt-3 sm:px-4">
          {/* Sidebar */}
          <aside
            className={`flex shrink-0 flex-col overflow-hidden rounded-[30px] bg-bg-secondary shadow-ambient backdrop-blur-xl transition-[width] duration-200 ${
              sidebarCollapsed ? "w-16" : "w-72"
            }`}
          >
            {sidebarCollapsed ? (
              <>
                <div className="flex flex-col items-center gap-3 px-2 py-4">
                  <button
                    type="button"
                    onClick={toggleSidebar}
                    className="flex h-10 w-10 items-center justify-center rounded-xl bg-bg-tertiary/80 text-base text-text-secondary transition-colors hover:bg-bg-hover hover:text-text-primary"
                    aria-label="ขยาย sidebar"
                    title="ขยาย sidebar"
                  >
                    ☰
                  </button>
                </div>

                <div className="flex-1 overflow-y-auto px-2 pb-3">
                  <div className="flex flex-col items-center gap-4">
                    <div className="flex flex-col items-center gap-2">
                      <span className="text-[9px] font-semibold uppercase tracking-[0.18em] text-text-muted">
                        Files
                      </span>
                      {files.slice(0, 4).map((f) => (
                        <button
                          key={f.name}
                          onClick={() => setPreviewFile(f.name)}
                          className="flex h-9 w-9 items-center justify-center rounded-xl text-sm text-text-primary transition-colors hover:bg-bg-hover"
                          title={`${f.name} · ${formatBytes(f.size)}`}
                          aria-label={`เปิดไฟล์ ${f.name}`}
                        >
                          {fileIcon(f.name)}
                        </button>
                      ))}
                      {files.length === 0 && (
                        <span className="text-[10px] text-text-muted">-</span>
                      )}
                    </div>

                    <div className="h-px w-8 bg-border" />

                    <div className="flex flex-col items-center gap-2">
                      <span className="text-[9px] font-semibold uppercase tracking-[0.18em] text-text-muted">
                        Chat
                      </span>
                      {sessions.slice(0, 5).map((s) => {
                        const isSelected = s.session_id === selectedSessionId;
                        return (
                          <button
                            key={s.session_id}
                            onClick={() => void handleSessionSelect(s.session_id)}
                            className={`flex h-9 w-9 items-center justify-center rounded-xl text-xs font-semibold transition-colors ${
                              isSelected
                                ? "bg-bg-active text-text-primary"
                                : "text-text-secondary hover:bg-bg-hover hover:text-text-primary"
                            }`}
                            title={`${s.first_message} · ${agentLabel(s.last_agent)}`}
                            aria-label={`เปิดเซสชัน ${s.first_message.slice(0, 20)}`}
                          >
                            {getSessionBadgeLabel(s.first_message)}
                          </button>
                        );
                      })}
                      {sessions.length === 0 && (
                        <span className="text-[10px] text-text-muted">-</span>
                      )}
                    </div>
                  </div>
                </div>

                <div className="px-2 py-3">
                  <button
                    onClick={() => setWorkspaceModalOpen(true)}
                    className="flex h-10 w-full items-center justify-center rounded-xl bg-bg-tertiary/70 text-base text-text-secondary transition-colors hover:bg-bg-hover hover:text-text-primary"
                    aria-label="เลือก workspace"
                    title={workspacePath || "เลือก workspace"}
                  >
                    📁
                  </button>
                </div>
              </>
            ) : (
              <>
                <div className="px-4 py-5">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="text-lg font-semibold tracking-tight text-text-primary">
                        AI Workspace
                      </p>
                      <p className="mt-1 text-xs text-text-muted">
                        เซสชัน ไฟล์ และ workspace ปัจจุบัน
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={toggleSidebar}
                      className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-bg-tertiary/80 text-base text-text-secondary transition-colors hover:bg-bg-hover hover:text-text-primary"
                      aria-label="ย่อ sidebar"
                      title="ย่อ sidebar"
                    >
                      ⇤
                    </button>
                  </div>
                </div>

                <div className="flex-1 overflow-y-auto">
                  <div className="px-4 py-3">
                    <span className="text-[11px] font-medium uppercase tracking-[0.18em] text-text-muted">
                      ไฟล์ ({files.length})
                    </span>
                  </div>
                  {files.length === 0 && (
                    <p className="px-4 py-6 text-center text-xs text-text-muted">
                      ยังไม่มีไฟล์
                    </p>
                  )}
                  <div className="px-2 py-2">
                    {files.map((f) => (
                      <div
                        key={f.name}
                        className="group flex cursor-pointer items-center gap-2 rounded-2xl px-2 py-2 hover:bg-bg-hover/70"
                      >
                        <span className="text-sm">{fileIcon(f.name)}</span>
                        <button
                          onClick={() => setPreviewFile(f.name)}
                          className="flex-1 truncate text-left text-sm text-text-primary"
                        >
                          {f.name}
                        </button>
                        <span className="text-[10px] text-text-muted">
                          {formatBytes(f.size)}
                        </span>
                        <button
                          onClick={() => handleDeleteFile(f.name)}
                          className="p-0.5 text-text-muted opacity-0 transition-all group-hover:opacity-100 hover:text-error"
                          aria-label={`ลบ ${f.name}`}
                        >
                          ×
                        </button>
                      </div>
                    ))}
                  </div>

                  <div className="mt-2 px-4 py-3">
                    <span className="text-[11px] font-medium uppercase tracking-[0.18em] text-text-muted">
                      เซสชัน ({sessions.length})
                    </span>
                  </div>
                  {sessions.length === 0 && (
                    <p className="px-4 py-6 text-center text-xs text-text-muted">
                      ยังไม่มีเซสชัน
                    </p>
                  )}
                  <div className="px-2 pb-4 pt-2">
                    {sessions.map((s) => (
                      <div
                        key={s.session_id}
                        className={`w-full rounded-2xl px-2 py-2 text-left transition-colors ${
                          s.session_id === selectedSessionId
                            ? "bg-bg-active text-accent"
                            : "hover:bg-bg-hover/70"
                        }`}
                      >
                        <div className="flex items-start gap-2">
                          <button
                            onClick={() => void handleSessionSelect(s.session_id)}
                            className="min-w-0 flex-1 text-left"
                          >
                            <p className="truncate text-sm text-text-primary">
                              {s.first_message.slice(0, 40)}
                            </p>
                            <p className="mt-1 text-[10px] text-text-muted">
                              {agentLabel(s.last_agent)} · {s.job_count} งาน
                            </p>
                          </button>
                          <button
                            onClick={(event) => {
                              event.stopPropagation();
                              void handleDeleteSession(s.session_id);
                            }}
                            className="shrink-0 px-1 text-text-muted transition-colors hover:text-error"
                            aria-label={`ลบเซสชัน ${s.first_message.slice(0, 20)}`}
                            title="ลบเซสชัน"
                          >
                            ×
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="px-4 py-4">
                  <button
                    onClick={() => setWorkspaceModalOpen(true)}
                    className="w-full rounded-2xl bg-bg-tertiary/70 px-3 py-3 text-left text-sm text-text-secondary transition-colors hover:bg-bg-hover hover:text-text-primary"
                    aria-label="เลือก workspace"
                    title={workspacePath || "เลือก workspace"}
                  >
                    <span className="mb-1 block text-[11px] uppercase tracking-[0.16em] text-text-muted">
                      Workspace
                    </span>
                    <span className="block truncate">
                      {workspacePath || "เลือก workspace..."}
                    </span>
                  </button>
                </div>
              </>
            )}
          </aside>

          {/* Chat area */}
          <div className="ml-3 flex min-h-0 flex-1 flex-col overflow-hidden rounded-[34px] bg-surface shadow-ambient backdrop-blur-xl">
            <div className="px-6 py-4">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-text-primary">
                    ห้องสนทนา
                  </p>
                  <p className="text-xs text-text-muted">
                    ตอบแบบสตรีมมิง จัดเก็บเป็นเซสชัน และทำงานตาม workspace ปัจจุบัน
                  </p>
                </div>
                <div className="hidden rounded-full border border-border bg-bg-tertiary/70 px-3 py-1.5 text-[11px] uppercase tracking-[0.16em] text-text-muted sm:block">
                  {theme === "dark" ? "Night Mode" : "Day Mode"}
                </div>
              </div>
            </div>
            <div className="flex-1 min-h-0 overflow-hidden">
              <ChatWindow
                messages={visibleMessages}
                isStreaming={isStreaming}
                statusMessage={statusMessage}
                hasError={hasError}
                errorMessage={errorMessage}
                isEmpty={visibleMessages.length === 0}
                onQuickAction={handleSend}
                isLoadingSession={isSwitchingSession}
              />
            </div>
            <InputArea
              onSend={handleSend}
              isStreaming={isStreaming}
              files={files}
            />
          </div>
        </div>

        {/* Preview Panel */}
        {previewFile && (
          <PreviewPanel
            key={previewFile}
            filename={previewFile}
            sessionId={sessionId}
            onClose={() => setPreviewFile(null)}
          />
        )}

        {/* Workspace Modal */}
        <WorkspaceModal
          isOpen={workspaceModalOpen}
          currentPath={workspacePath}
          sessionId={sessionId}
          onClose={() => setWorkspaceModalOpen(false)}
          onSwitch={handleWorkspaceSwitch}
        />

        {/* Format Modal */}
        <FormatModal
          isOpen={formatModalOpen}
          filename={pendingFilename}
          agentLabel={pendingAgentLabel}
          onClose={() => setFormatModalOpen(false)}
          onConfirm={(format) => {
            setFormatModalOpen(false);
            saveRequestRef.current = true;
            submitMessage("บันทึก", {
              outputFormat: format,
              forcePendingState: true,
            });
          }}
        />

        {/* Delete Confirm Modal */}
        <DeleteConfirmModal
          isOpen={deleteModalOpen}
          filename={deleteFilename}
          onClose={() => setDeleteModalOpen(false)}
          onConfirm={confirmDelete}
        />
      </div>
    </ErrorBoundary>
  );
}
