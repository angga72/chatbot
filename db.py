# ===== Database layer (PostgreSQL di Docker) =====
# Tanggung jawab:
#  - Simpan & muat riwayat chat per session (MEMORY jangka panjang)
#  - Cache data knowledge dari Google Sheet (biar gak fetch tiap pesan)
import json
import hashlib
from datetime import datetime, timezone

import psycopg2
import psycopg2.extras

from config import DATABASE_URL

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS chat_history (
    id BIGSERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user','assistant','system')),
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_chat_session ON chat_history(session_id, created_at);

CREATE TABLE IF NOT EXISTS knowledge_cache (
    id SERIAL PRIMARY KEY,
    source TEXT NOT NULL DEFAULT 'google_sheet',
    data_hash TEXT,
    payload JSONB,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS feedback_log (
    id BIGSERIAL PRIMARY KEY,
    session_id TEXT,
    message TEXT,
    feedback TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""


def ensure_schema():
    """Auto-create tabel kalau belum ada (aman dipanggil tiap startup)."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(SCHEMA_SQL)


def get_conn():
    """Buat koneksi baru. App Streamlit = multi-thread, jangan share koneksi antar request."""
    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL belum di-set. Isi di file .env (lokal) atau Secrets dashboard "
            "(Streamlit Cloud). Contoh: postgresql://user:pass@host:port/dbname"
        )
    conn = psycopg2.connect(DATABASE_URL, connect_timeout=5)
    conn.autocommit = True
    return conn


# ---------- Chat history (memory) ----------

def save_message(session_id: str, role: str, content: str):
    """Simpan satu pesan chat ke PostgreSQL."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO chat_history (session_id, role, content) VALUES (%s, %s, %s)",
                (session_id, role, content),
            )


def load_history(session_id: str, limit: int = 30):
    """Muat riwayat chat terakhir untuk sebuah sesi (user + assistant saja)."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT role, content FROM chat_history
                WHERE session_id = %s
                ORDER BY id DESC LIMIT %s
                """,
                (session_id, limit),
            )
            rows = cur.fetchall()
    # balikin urutan kronologis (yang paling lama dulu)
    return list(reversed(rows))


def clear_history(session_id: str):
    """Hapus riwayat chat sebuah sesi."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM chat_history WHERE session_id = %s", (session_id,))


def get_all_sessions():
    """Daftar session_id + jumlah pesan (buat sidebar 'memory' info)."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT session_id, COUNT(*) AS n, MAX(created_at) AS last_seen
                FROM chat_history GROUP BY session_id ORDER BY last_seen DESC
                """
            )
            return cur.fetchall()


# ---------- Knowledge cache (Google Sheet) ----------

def _hash_payload(payload):
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def save_knowledge(payload, source="google_sheet"):
    """Simpan/update cache knowledge. Satu baris per source (upsert manual)."""
    data_hash = _hash_payload(payload)
    now = datetime.now(timezone.utc)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM knowledge_cache WHERE source = %s", (source,))
            row = cur.fetchone()
            if row:
                cur.execute(
                    "UPDATE knowledge_cache SET payload=%s, data_hash=%s, updated_at=%s WHERE source=%s",
                    (json.dumps(payload), data_hash, now, source),
                )
            else:
                cur.execute(
                    "INSERT INTO knowledge_cache (source, payload, data_hash, updated_at) VALUES (%s,%s,%s,%s)",
                    (source, json.dumps(payload), data_hash, now),
                )
    return data_hash


def load_knowledge(source="google_sheet"):
    """Ambil cache knowledge terakhir."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT payload, data_hash, updated_at FROM knowledge_cache WHERE source = %s",
                (source,),
            )
            row = cur.fetchone()
    if not row:
        return None
    # psycopg2 kadang auto-parse JSONB jadi dict, kadang masih string -> tangani dua-duanya
    payload = row["payload"]
    if isinstance(payload, str):
        payload = json.loads(payload)
    row["payload"] = payload
    return row


# ---------- Feedback ----------

def save_feedback(session_id: str, message: str, feedback: str):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO feedback_log (session_id, message, feedback) VALUES (%s,%s,%s)",
                (session_id, message, feedback),
            )
