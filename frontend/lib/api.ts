// ─── Types ───────────────────────────────────────────────────────────

export interface Job {
  id: string;
  created_at: string;
  session_id: string | null;
  user_input: string;
  agent: string | null;
  reason: string | null;
  status: "pending" | "completed" | "error" | "discarded";
  output_text: string | null;
  files?: SavedFile[];
}

export interface SavedFile {
  job_id: string;
  filename: string;
  agent: string | null;
  size_bytes: number;
  created_at: string;
}

export interface Session {
  session_id: string;
  first_message: string;
  last_active: string;
  created_at: string;
  job_count: number;
  last_agent: string;
}

export interface WorkspaceInfo {
  name: string;
  path: string;
  active?: boolean;
}

export interface HealthResponse {
  status: string;
  model: string;
  workspace: string;
  db: {
    available: boolean;
    path: string;
  };
}

export interface PreviewResponse {
  filename: string;
  content: string;
  ext: string;
  size: number;
}

export interface ChatRequest {
  message: string;
  conversation_history?: Array<{ role: string; content: string }>;
  session_id?: string;
  pending_doc?: string;
  pending_agent?: string;
  pending_temp_paths?: string[];
  agent_types?: string[];
  output_format?: string;
  output_formats?: string[];
  overwrite_filename?: string;
  local_agent_mode?: boolean;
}

export interface WorkspaceRequest {
  path: string;
  session_id?: string;
}

export interface NewWorkspaceRequest {
  name: string;
}

export interface DeleteRequest {
  filename: string;
}

// ─── Config ──────────────────────────────────────────────────────────

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000";

async function request<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error(error.error || `HTTP ${res.status}`);
  }

  return res.json();
}

// ─── Health & Info ───────────────────────────────────────────────────

export async function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/api/health");
}

// ─── Chat (SSE) ──────────────────────────────────────────────────────

export function postChatStream(
  body: ChatRequest,
  onEvent: (event: Record<string, unknown>) => void,
  onError: (error: Error) => void,
  onDone: () => void
): AbortController {
  const controller = new AbortController();

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
        const lines = buffer.split("\n\n");
        buffer = lines.pop() || "";

        for (const chunk of lines) {
          const dataLine = chunk
            .split("\n")
            .find((line) => line.startsWith("data: "));
          if (!dataLine) continue;

          try {
            const event = JSON.parse(dataLine.slice(6));
            onEvent(event);
          } catch {
            // Skip malformed events
          }
        }
      }

      onDone();
    })
    .catch((err) => {
      if (err.name !== "AbortError") {
        onError(err);
      }
    });

  return controller;
}

// ─── History ─────────────────────────────────────────────────────────

export async function getHistory(
  limit = 50
): Promise<{ jobs: Job[]; db_available: boolean }> {
  return request(`/api/history?limit=${limit}`);
}

export async function getJob(jobId: string): Promise<Job> {
  return request(`/api/history/${jobId}`);
}

// ─── Sessions ────────────────────────────────────────────────────────

export async function getSessions(): Promise<{ sessions: Session[] }> {
  return request("/api/sessions");
}

export async function getSessionJobs(
  sessionId: string
): Promise<{ jobs: Array<{ id: string; created_at: string; user_input: string; agent: string; output_text: string }> }> {
  return request(`/api/sessions/${sessionId}`);
}

// ─── Files ───────────────────────────────────────────────────────────

export async function getFiles(): Promise<{ files: Array<{ name: string; size: number; modified: string }> }> {
  return request("/api/files");
}

export async function getPreview(filename: string): Promise<PreviewResponse> {
  return request(`/api/preview?file=${encodeURIComponent(filename)}`);
}

export async function deleteFile(filename: string): Promise<{ success: boolean; filename: string }> {
  return request("/api/delete", {
    method: "POST",
    body: JSON.stringify({ filename }),
  });
}

export function getFileUrl(filename: string): string {
  return `${API_BASE}/api/serve/${encodeURIComponent(filename)}`;
}

// ─── Workspace ───────────────────────────────────────────────────────

export async function getWorkspace(): Promise<{ workspace: string }> {
  return request("/api/workspace");
}

export async function setWorkspace(
  body: WorkspaceRequest
): Promise<{ workspace: string }> {
  return request("/api/workspace", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function getWorkspaces(): Promise<{ workspaces: WorkspaceInfo[] }> {
  return request("/api/workspaces");
}

export async function createWorkspace(
  body: NewWorkspaceRequest
): Promise<{ workspace: string }> {
  return request("/api/workspace/new", {
    method: "POST",
    body: JSON.stringify(body),
  });
}
