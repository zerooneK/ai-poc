"use client";

import { useState } from "react";
import { X, FolderPlus, Check, Folder } from "lucide-react";
import { cn } from "@/lib/utils";
import { getWorkspaces, setWorkspace, createWorkspace, type WorkspaceInfo } from "@/lib/api";

interface WorkspaceModalProps {
  isOpen: boolean;
  currentPath: string;
  onClose: () => void;
  onSwitch: (path: string) => void;
}

export default function WorkspaceModal({
  isOpen,
  currentPath,
  onClose,
  onSwitch,
}: WorkspaceModalProps) {
  const [workspaces, setWorkspaces] = useState<WorkspaceInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [newName, setNewName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  if (isOpen && workspaces.length === 0) {
    setLoading(true);
    getWorkspaces()
      .then((res) => {
        setWorkspaces(
          res.workspaces.map((w) => ({
            ...w,
            active: w.path === currentPath,
          }))
        );
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }

  const handleSwitch = (ws: WorkspaceInfo) => {
    setWorkspace({ path: ws.path })
      .then(() => {
        onSwitch(ws.path);
        onClose();
      })
      .catch((err) => setError(err.message));
  };

  const handleCreate = () => {
    if (!newName.trim()) return;
    setCreating(true);
    setError(null);
    createWorkspace({ name: newName.trim() })
      .then((res) => {
        onSwitch(res.workspace);
        setNewName("");
        setCreating(false);
        onClose();
      })
      .catch((err) => {
        setError(err.message);
        setCreating(false);
      });
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-bg-secondary rounded-xl border border-border w-[480px] max-h-[80vh] flex flex-col shadow-xl">
        <div className="flex items-center justify-between px-5 py-4 border-b border-border">
          <h2 className="text-base font-semibold text-text-primary">
            🗂️ เลือก Workspace
          </h2>
          <button
            onClick={onClose}
            className="p-1 rounded hover:bg-bg-hover text-text-muted transition-colors"
            aria-label="ปิด"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-4">
          {loading && (
            <p className="text-sm text-text-muted text-center py-4">
              กำลังโหลด...
            </p>
          )}
          {!loading && workspaces.length === 0 && (
            <p className="text-sm text-text-muted text-center py-4">
              ยังไม่มีโฟลเดอร์
            </p>
          )}
          <div className="space-y-1">
            {workspaces.map((ws) => (
              <button
                key={ws.path}
                onClick={() => handleSwitch(ws)}
                className={cn(
                  "w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-colors",
                  ws.active
                    ? "bg-accent/10 text-accent"
                    : "hover:bg-bg-hover text-text-primary"
                )}
              >
                {ws.active ? (
                  <Check className="w-4 h-4 flex-shrink-0" />
                ) : (
                  <Folder className="w-4 h-4 flex-shrink-0 text-text-muted" />
                )}
                <span className="text-sm truncate">{ws.name}</span>
              </button>
            ))}
          </div>
        </div>

        <div className="px-5 py-4 border-t border-border">
          <div className="flex items-center gap-2">
            <FolderPlus className="w-4 h-4 text-text-muted flex-shrink-0" />
            <input
              type="text"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleCreate()}
              placeholder="ชื่อโฟลเดอร์ใหม่..."
              className="flex-1 bg-bg-tertiary border border-border rounded-lg px-3 py-2 text-sm text-text-primary placeholder:text-text-muted outline-none focus:border-accent"
            />
            <button
              onClick={handleCreate}
              disabled={!newName.trim() || creating}
              className={cn(
                "px-3 py-2 text-sm rounded-lg transition-colors",
                newName.trim() && !creating
                  ? "bg-accent hover:bg-accent-hover text-white"
                  : "bg-bg-hover text-text-muted cursor-not-allowed"
              )}
            >
              สร้าง
            </button>
          </div>
          {error && (
            <p className="text-xs text-error mt-2">❌ {error}</p>
          )}
        </div>
      </div>
    </div>
  );
}
