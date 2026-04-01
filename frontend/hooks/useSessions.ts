"use client";

import { useState, useCallback } from "react";
import { getSessions, getSessionJobs, type Session } from "@/lib/api";

export interface SessionJob {
  id: string;
  created_at: string;
  user_input: string;
  agent: string;
  output_text: string;
}

export function useSessions() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadSessions = useCallback(() => {
    setLoading(true);
    setError(null);
    getSessions()
      .then((res) => setSessions(res.sessions))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const loadSessionJobs = useCallback((sessionId: string) => {
    return getSessionJobs(sessionId);
  }, []);

  return {
    sessions,
    loading,
    error,
    loadSessions,
    loadSessionJobs,
  };
}
