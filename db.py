"""
db.py — SQLite persistence layer for AI Assistant
──────────────────────────────────────────────────
Graceful degradation: every public function catches its own exceptions
and returns a safe default (None / [] / '').
DB errors are logged but NEVER propagate to the chat/SSE flow.

Tables:
  jobs        — one row per user request sent to the Orchestrator
  saved_files — one row per file written to workspace
"""
import sqlite3
import uuid
import logging
import os
import threading
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# Module-level write lock for thread-safe SQLite writes
_db_write_lock = threading.Lock()

_DB_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'data', 'assistant.db'
)

# Global flag — set by init_db(). All functions check this first.
DB_AVAILABLE: bool = False


# ─── Internal helpers ─────────────────────────────────────────────────────────

def _connect() -> sqlite3.Connection:
    """Open a connection with WAL mode and 5-second busy timeout."""
    conn = sqlite3.connect(_DB_PATH, timeout=5, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─── Startup ──────────────────────────────────────────────────────────────────

def init_db() -> None:
    """Create tables, run integrity check, and clean up zombie jobs.
    Sets DB_AVAILABLE = True on success, False on any error.
    Called once at Flask startup — safe to call again (idempotent)."""
    global DB_AVAILABLE
    try:
        os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)

        with _connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id          TEXT PRIMARY KEY,
                    created_at  TEXT NOT NULL,
                    session_id  TEXT,
                    user_input  TEXT NOT NULL,
                    agent       TEXT,
                    reason      TEXT,
                    status      TEXT NOT NULL DEFAULT 'pending',
                    output_text TEXT
                );

                CREATE TABLE IF NOT EXISTS saved_files (
                    id          TEXT PRIMARY KEY,
                    job_id      TEXT NOT NULL,
                    created_at  TEXT NOT NULL,
                    filename    TEXT NOT NULL,
                    agent       TEXT,
                    size_bytes  INTEGER DEFAULT 0,
                    FOREIGN KEY (job_id) REFERENCES jobs(id)
                );

                CREATE INDEX IF NOT EXISTS idx_jobs_created
                    ON jobs(created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_files_job_id
                    ON saved_files(job_id);
            """)

            # Integrity check — if DB is corrupted, fail fast
            result = conn.execute("PRAGMA integrity_check").fetchone()
            if result[0] != 'ok':
                raise RuntimeError(f"DB integrity_check failed: {result[0]}")

            # Zombie cleanup: any job stuck in 'pending' for over 1 hour
            # is marked 'error' (happens when Flask restarts mid-stream)
            conn.execute("""
                UPDATE jobs SET status = 'error'
                WHERE status = 'pending'
                AND created_at < datetime('now', '-1 hour')
            """)

        DB_AVAILABLE = True
        logger.info(f"[db] Ready — {_DB_PATH}")

    except Exception as e:
        DB_AVAILABLE = False
        logger.warning(f"[db] Unavailable — history disabled. Reason: {e}")


# ─── Write operations ─────────────────────────────────────────────────────────

def create_job(user_input: str, session_id: Optional[str] = None) -> Optional[str]:
    """Insert a new job row (status='pending'). Returns job_id or None on error."""
    if not DB_AVAILABLE:
        return None
    try:
        job_id = str(uuid.uuid4())
        with _db_write_lock:
            with _connect() as conn:
                conn.execute(
                    "INSERT INTO jobs (id, created_at, session_id, user_input, status)"
                    " VALUES (?, ?, ?, ?, 'pending')",
                    (job_id, _now(), session_id, user_input)
                )
        return job_id
    except Exception as e:
        logger.warning(f"[db] create_job failed: {e}")
        return None


def update_job_agent(job_id: Optional[str], agent: str, reason: str) -> None:
    """Update job with orchestrator routing result."""
    if not DB_AVAILABLE or not job_id:
        return
    try:
        with _db_write_lock:
            with _connect() as conn:
                conn.execute(
                    "UPDATE jobs SET agent = ?, reason = ? WHERE id = ?",
                    (agent, reason, job_id)
                )
    except Exception as e:
        logger.warning(f"[db] update_job_agent failed: {e}")


def complete_job(job_id: Optional[str], output_text: str) -> None:
    """Mark job as completed and store the full AI output."""
    if not DB_AVAILABLE or not job_id:
        return
    try:
        with _db_write_lock:
            with _connect() as conn:
                conn.execute(
                    "UPDATE jobs SET status = 'completed', output_text = ? WHERE id = ?",
                    (output_text, job_id)
                )
    except Exception as e:
        logger.warning(f"[db] complete_job failed: {e}")


def fail_job(job_id: Optional[str]) -> None:
    """Mark job as error (used on exceptions and discards)."""
    if not DB_AVAILABLE or not job_id:
        return
    try:
        with _db_write_lock:
            with _connect() as conn:
                conn.execute(
                    "UPDATE jobs SET status = 'error' WHERE id = ?",
                    (job_id,)
                )
    except Exception as e:
        logger.warning(f"[db] fail_job failed: {e}")


def discard_job(job_id: Optional[str]) -> None:
    """Mark job as discarded (user cancelled before saving)."""
    if not DB_AVAILABLE or not job_id:
        return
    try:
        with _db_write_lock:
            with _connect() as conn:
                conn.execute(
                    "UPDATE jobs SET status = 'discarded' WHERE id = ?",
                    (job_id,)
                )
    except Exception as e:
        logger.warning(f"[db] discard_job failed: {e}")


def record_file(job_id: Optional[str], filename: str,
                agent: str, size_bytes: int = 0) -> None:
    """Insert a saved_files row. Silently skips if job_id is None."""
    if not DB_AVAILABLE or not job_id:
        return
    try:
        with _db_write_lock:
            with _connect() as conn:
                conn.execute(
                    "INSERT INTO saved_files (id, job_id, created_at, filename, agent, size_bytes)"
                    " VALUES (?, ?, ?, ?, ?, ?)",
                    (str(uuid.uuid4()), job_id, _now(), filename, agent, size_bytes)
                )
    except Exception as e:
        logger.warning(f"[db] record_file failed: {e}")


# ─── Read operations ──────────────────────────────────────────────────────────

def get_history(limit: int = 50) -> list:
    """Return recent jobs with their saved files. Returns [] on any error."""
    if not DB_AVAILABLE:
        return []
    try:
        with _connect() as conn:
            jobs = conn.execute(
                """SELECT id, created_at, session_id, user_input,
                          agent, reason, status, output_text
                   FROM jobs
                   ORDER BY created_at DESC
                   LIMIT ?""",
                (limit,)
            ).fetchall()

            if not jobs:
                return []

            job_ids = [j['id'] for j in jobs]
            placeholders = ','.join('?' * len(job_ids))
            all_files = conn.execute(
                f"""SELECT job_id, filename, agent, size_bytes, created_at
                    FROM saved_files
                    WHERE job_id IN ({placeholders})
                    ORDER BY created_at""",
                job_ids
            ).fetchall()

            files_by_job = {}
            for f in all_files:
                files_by_job.setdefault(f['job_id'], []).append(dict(f))

            return [
                {**dict(job), 'files': files_by_job.get(job['id'], [])}
                for job in jobs
            ]

    except Exception as e:
        logger.warning(f"[db] get_history failed: {e}")
        return []


def get_job(job_id: str) -> Optional[dict]:
    """Return a single job with its files, or None on error / not found."""
    if not DB_AVAILABLE:
        return None
    try:
        with _connect() as conn:
            job = conn.execute(
                "SELECT * FROM jobs WHERE id = ?", (job_id,)
            ).fetchone()
            if not job:
                return None
            files = conn.execute(
                """SELECT filename, agent, size_bytes, created_at
                   FROM saved_files WHERE job_id = ? ORDER BY created_at""",
                (job_id,)
            ).fetchall()
            return {**dict(job), 'files': [dict(f) for f in files]}
    except Exception as e:
        logger.warning(f"[db] get_job failed: {e}")
        return None


def get_sessions(limit: int = 20) -> list:
    """Return sessions ordered by most recent activity."""
    if not DB_AVAILABLE:
        return []
    try:
        with _connect() as conn:
            rows = conn.execute("""
                SELECT
                    j.session_id,
                    (SELECT user_input FROM jobs
                     WHERE session_id = j.session_id
                     ORDER BY created_at ASC LIMIT 1) AS first_message,
                    MAX(j.created_at) AS last_active,
                    MIN(j.created_at) AS created_at,
                    COUNT(*) AS job_count,
                    (SELECT agent FROM jobs
                     WHERE session_id = j.session_id AND agent IS NOT NULL
                     ORDER BY created_at DESC LIMIT 1) AS last_agent
                FROM jobs j
                WHERE j.session_id IS NOT NULL
                GROUP BY j.session_id
                ORDER BY last_active DESC
                LIMIT ?
            """, (limit,)).fetchall()
            return [dict(r) for r in rows]
    except Exception as e:
        logger.warning(f"[db] get_sessions failed: {e}")
        return []


def get_session_jobs(session_id: str) -> list:
    """Return completed jobs for a session, oldest first."""
    if not DB_AVAILABLE:
        return []
    try:
        with _connect() as conn:
            rows = conn.execute("""
                SELECT id, created_at, user_input, agent, output_text
                FROM jobs
                WHERE session_id = ? AND status = 'completed'
                ORDER BY created_at ASC
            """, (session_id,)).fetchall()
            return [dict(r) for r in rows]
    except Exception as e:
        logger.warning(f"[db] get_session_jobs failed: {e}")
        return []


def delete_session(session_id: str) -> bool:
    """Delete all jobs and file records for a session."""
    if not DB_AVAILABLE:
        return False
    try:
        with _db_write_lock:
            with _connect() as conn:
                conn.execute("""
                    DELETE FROM saved_files
                    WHERE job_id IN (
                        SELECT id FROM jobs WHERE session_id = ?
                    )
                """, (session_id,))
                result = conn.execute(
                    "DELETE FROM jobs WHERE session_id = ?",
                    (session_id,)
                )
                return result.rowcount > 0
    except Exception as e:
        logger.warning(f"[db] delete_session failed: {e}")
        return False


def db_status() -> dict:
    """Return DB health info for /api/health endpoint."""
    return {
        'available': DB_AVAILABLE,
        'path': _DB_PATH if DB_AVAILABLE else None
    }
