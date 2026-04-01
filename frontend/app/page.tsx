"use client";

import { useState, useCallback, useEffect } from "react";
import { useSSE } from "@/hooks/useSSE";
import { useFileSSE } from "@/hooks/useFileSSE";
import { useSessions } from "@/hooks/useSessions";
import ChatWindow from "@/components/ChatWindow";
import InputArea from "@/components/InputArea";
import PreviewPanel from "@/components/PreviewPanel";
import WorkspaceModal from "@/components/WorkspaceModal";
import FormatModal from "@/components/FormatModal";
import DeleteConfirmModal from "@/components/DeleteConfirmModal";
import { getFiles, deleteFile } from "@/lib/api";
import { fileIcon, formatBytes, agentLabel } from "@/lib/utils";

interface Message {
  role: "user" | "assistant";
  content: string;
  agent?: string;
}

interface WorkspaceFile {
  name: string;
  size: number;
  modified: string;
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [conversationHistory, setConversationHistory] = useState<
    Array<{ role: string; content: string }>
  >([]);
  const [workspacePath, setWorkspacePath] = useState("");
  const [files, setFiles] = useState<WorkspaceFile[]>([]);
  const [workspaceModalOpen, setWorkspaceModalOpen] = useState(false);
  const [previewFile, setPreviewFile] = useState<string | null>(null);
  const [formatModalOpen, setFormatModalOpen] = useState(false);
  const [pendingFilename, _setPendingFilename] = useState("");
  const [pendingAgentLabel, _setPendingAgentLabel] = useState("");
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [deleteFilename, setDeleteFilename] = useState("");

  const {
    _outputText,
    statusMessage,
    isStreaming,
    hasError,
    errorMessage,
    _lastEvent,
    sendMessage,
  } = useSSE();

  const { fileChanged } = useFileSSE();
  const { sessions, loadSessions } = useSessions();

  // Load files on mount and when fileChanged updates
  useEffect(() => {
    getFiles()
      .then((res) => setFiles(res.files))
      .catch(() => {});
  }, [fileChanged]);

  // Load sessions on mount
  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  const handleStreamComplete = useCallback(
    (outputText: string, agent?: string) => {
      const assistantMsg: Message = {
        role: "assistant",
        content: outputText,
        agent,
      };
      setMessages((prev) => [...prev, assistantMsg]);
      setConversationHistory((prev) => [
        ...prev,
        { role: "assistant", content: outputText },
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
        onStreamComplete: (payload) => {
          handleStreamComplete(payload.outputText, payload.agent);
        },
      });
    },
    [conversationHistory, sendMessage, handleStreamComplete]
  );

  const handleWorkspaceSwitch = (path: string) => {
    setWorkspacePath(path);
    setFiles([]);
    setConversationHistory([]);
    setMessages([]);
  };

  const handleDeleteFile = (filename: string) => {
    setDeleteFilename(filename);
    setDeleteModalOpen(true);
  };

  const confirmDelete = () => {
    deleteFile(deleteFilename)
      .then(() => {
        setDeleteModalOpen(false);
        getFiles()
          .then((res) => setFiles(res.files))
          .catch(() => {});
      })
      .catch(() => {});
  };

  return (
    <div className="flex flex-col h-full relative">
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <aside className="w-72 bg-bg-secondary border-r border-border flex flex-col shrink-0">
          <div className="px-4 py-3 border-b border-border">
            <button
              onClick={() => setWorkspaceModalOpen(true)}
              className="w-full flex items-center gap-2 text-sm text-text-secondary hover:text-text-primary transition-colors"
            >
              <span className="truncate">
                {workspacePath || "เลือก workspace..."}
              </span>
            </button>
          </div>

          <div className="flex-1 overflow-y-auto">
            <div className="px-4 py-2 border-b border-border">
              <span className="text-xs font-medium text-text-muted uppercase tracking-wide">
                ไฟล์ ({files.length})
              </span>
            </div>
            {files.length === 0 && (
              <p className="text-xs text-text-muted px-4 py-3 text-center">
                ยังไม่มีไฟล์
              </p>
            )}
            <div className="px-2">
              {files.map((f) => (
                <div
                  key={f.name}
                  className="flex items-center gap-2 px-2 py-1.5 rounded hover:bg-bg-hover cursor-pointer group"
                >
                  <span className="text-sm">{fileIcon(f.name)}</span>
                  <button
                    onClick={() => setPreviewFile(f.name)}
                    className="flex-1 text-left text-sm text-text-primary truncate"
                  >
                    {f.name}
                  </button>
                  <span className="text-[10px] text-text-muted">
                    {formatBytes(f.size)}
                  </span>
                  <button
                    onClick={() => handleDeleteFile(f.name)}
                    className="opacity-0 group-hover:opacity-100 text-text-muted hover:text-error transition-all p-0.5"
                    aria-label={`ลบ ${f.name}`}
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>

            <div className="px-4 py-2 border-b border-border mt-2">
              <span className="text-xs font-medium text-text-muted uppercase tracking-wide">
                เซสชัน ({sessions.length})
              </span>
            </div>
            {sessions.length === 0 && (
              <p className="text-xs text-text-muted px-4 py-3 text-center">
                ยังไม่มีเซสชัน
              </p>
            )}
            <div className="px-2 pb-4">
              {sessions.map((s) => (
                <button
                  key={s.session_id}
                  className="w-full text-left px-2 py-2 rounded hover:bg-bg-hover transition-colors"
                >
                  <p className="text-sm text-text-primary truncate">
                    {s.first_message.slice(0, 40)}
                  </p>
                  <p className="text-[10px] text-text-muted mt-0.5">
                    {agentLabel(s.last_agent)} · {s.job_count} งาน
                  </p>
                </button>
              ))}
            </div>
          </div>
        </aside>

        {/* Chat area */}
        <div className="flex flex-col flex-1 min-w-0">
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
      </div>

      {/* Preview Panel */}
      {previewFile && (
        <PreviewPanel
          filename={previewFile}
          onClose={() => setPreviewFile(null)}
        />
      )}

      {/* Workspace Modal */}
      <WorkspaceModal
        isOpen={workspaceModalOpen}
        currentPath={workspacePath}
        onClose={() => setWorkspaceModalOpen(false)}
        onSwitch={handleWorkspaceSwitch}
      />

      {/* Format Modal */}
      <FormatModal
        isOpen={formatModalOpen}
        filename={pendingFilename}
        agentLabel={pendingAgentLabel}
        onClose={() => setFormatModalOpen(false)}
        onConfirm={() => setFormatModalOpen(false)}
      />

      {/* Delete Confirm Modal */}
      <DeleteConfirmModal
        isOpen={deleteModalOpen}
        filename={deleteFilename}
        onClose={() => setDeleteModalOpen(false)}
        onConfirm={confirmDelete}
      />
    </div>
  );
}
