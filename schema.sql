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
