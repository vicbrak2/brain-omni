-- ============================================================
-- Brain Omni — Schema inicial
-- Migración: 001_initial_schema
-- ============================================================

-- Extensiones
CREATE EXTENSION IF NOT EXISTS "pgcrypto";  -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS "vector";    -- pgvector para embeddings

-- ── Helper: updated_at automático ─────────────────────────────────────────
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


-- ════════════════════════════════════════════════════════════
-- 1. tenants
-- ════════════════════════════════════════════════════════════
CREATE TABLE tenants (
    id          UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    slug        TEXT         UNIQUE NOT NULL,             -- identificador URL-friendly
    name        TEXT         NOT NULL,
    plan        TEXT         NOT NULL DEFAULT 'free'
                             CHECK (plan IN ('free','starter','pro','enterprise')),
    is_active   BOOLEAN      NOT NULL DEFAULT TRUE,
    metadata    JSONB        NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TRIGGER tenants_updated_at
    BEFORE UPDATE ON tenants
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();


-- ════════════════════════════════════════════════════════════
-- 2. phone_numbers
-- ════════════════════════════════════════════════════════════
CREATE TABLE phone_numbers (
    id               UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id        UUID         NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    waba_id          TEXT         NOT NULL,                -- WhatsApp Business Account ID
    phone_number_id  TEXT         UNIQUE NOT NULL,         -- ID de Meta
    display_number   TEXT         NOT NULL,                -- ej. +56912345678
    display_name     TEXT,
    is_active        BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_phone_numbers_tenant ON phone_numbers(tenant_id);

CREATE TRIGGER phone_numbers_updated_at
    BEFORE UPDATE ON phone_numbers
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();


-- ════════════════════════════════════════════════════════════
-- 3. conversations
-- ════════════════════════════════════════════════════════════
CREATE TABLE conversations (
    id               UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id        UUID         NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    phone_number_id  UUID         NOT NULL REFERENCES phone_numbers(id),
    contact_wa_id    TEXT         NOT NULL,  -- WhatsApp ID del cliente
    contact_name     TEXT,
    channel          TEXT         NOT NULL DEFAULT 'whatsapp'
                                  CHECK (channel IN ('whatsapp','instagram','facebook','tiktok','web')),
    status           TEXT         NOT NULL DEFAULT 'bot'
                                  CHECK (status IN ('bot','open','resolved','human')),
    metadata         JSONB        NOT NULL DEFAULT '{}',
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, phone_number_id, contact_wa_id)
);

CREATE INDEX idx_conversations_tenant    ON conversations(tenant_id);
CREATE INDEX idx_conversations_status   ON conversations(tenant_id, status);
CREATE INDEX idx_conversations_contact  ON conversations(tenant_id, contact_wa_id);

CREATE TRIGGER conversations_updated_at
    BEFORE UPDATE ON conversations
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();


-- ════════════════════════════════════════════════════════════
-- 4. messages
-- ════════════════════════════════════════════════════════════
CREATE TABLE messages (
    id               UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id        UUID         NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    conversation_id  UUID         NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    wamid            TEXT         UNIQUE,        -- WhatsApp msg ID (idempotencia)
    direction        TEXT         NOT NULL CHECK (direction IN ('inbound','outbound')),
    role             TEXT         NOT NULL CHECK (role IN ('user','assistant','system')),
    content_type     TEXT         NOT NULL DEFAULT 'text'
                                  CHECK (content_type IN ('text','image','audio','document','location','reaction')),
    content          TEXT,
    content_url      TEXT,
    is_processed     BOOLEAN      NOT NULL DEFAULT FALSE,
    metadata         JSONB        NOT NULL DEFAULT '{}',
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_messages_conversation  ON messages(conversation_id, created_at);
CREATE INDEX idx_messages_tenant        ON messages(tenant_id);
CREATE INDEX idx_messages_unprocessed   ON messages(tenant_id, is_processed)
    WHERE is_processed = FALSE;


-- ════════════════════════════════════════════════════════════
-- 5. agent_config
-- ════════════════════════════════════════════════════════════
CREATE TABLE agent_config (
    id                  UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID          NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    phone_number_id     UUID          REFERENCES phone_numbers(id) ON DELETE CASCADE,
    -- NULL en phone_number_id = config global del tenant
    model               TEXT          NOT NULL DEFAULT 'claude-haiku-4-5-20251001',
    system_prompt       TEXT          NOT NULL DEFAULT '',
    temperature         NUMERIC(3,2)  NOT NULL DEFAULT 0.70
                                      CHECK (temperature BETWEEN 0.0 AND 1.0),
    max_tokens          INTEGER       NOT NULL DEFAULT 1024,
    handoff_enabled     BOOLEAN       NOT NULL DEFAULT FALSE,
    handoff_threshold   INTEGER       NOT NULL DEFAULT 5,  -- msgs antes de escalar a humano
    business_hours      JSONB         NOT NULL DEFAULT '{}',
    created_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, phone_number_id)
);

CREATE TRIGGER agent_config_updated_at
    BEFORE UPDATE ON agent_config
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();


-- ════════════════════════════════════════════════════════════
-- 6. knowledge_docs
-- ════════════════════════════════════════════════════════════
CREATE TABLE knowledge_docs (
    id          UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID         NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    title       TEXT         NOT NULL,
    content     TEXT         NOT NULL,
    source_url  TEXT,
    doc_type    TEXT         NOT NULL DEFAULT 'faq'
                             CHECK (doc_type IN ('faq','product','policy','custom')),
    is_active   BOOLEAN      NOT NULL DEFAULT TRUE,
    metadata    JSONB        NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_knowledge_docs_tenant ON knowledge_docs(tenant_id, is_active);

CREATE TRIGGER knowledge_docs_updated_at
    BEFORE UPDATE ON knowledge_docs
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();


-- ════════════════════════════════════════════════════════════
-- 7. embeddings  (requiere pgvector)
-- ════════════════════════════════════════════════════════════
CREATE TABLE embeddings (
    id           UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id    UUID         NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    doc_id       UUID         NOT NULL REFERENCES knowledge_docs(id) ON DELETE CASCADE,
    chunk_index  INTEGER      NOT NULL DEFAULT 0,
    chunk_text   TEXT         NOT NULL,
    embedding    VECTOR(1536),  -- dimensiones para text-embedding-3-small
    model        TEXT         NOT NULL DEFAULT 'text-embedding-3-small',
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    UNIQUE(doc_id, chunk_index)
);

-- IVFFlat para búsqueda aproximada por coseno
-- Ajustar lists = sqrt(num_rows) cuando la tabla tenga datos reales
CREATE INDEX idx_embeddings_vector ON embeddings
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE INDEX idx_embeddings_tenant ON embeddings(tenant_id);


-- ════════════════════════════════════════════════════════════
-- Row-Level Security (RLS)
-- ════════════════════════════════════════════════════════════
--
-- La app establece el tenant en cada request:
--   await conn.execute("SET LOCAL app.current_tenant_id = $1", tenant_id)
--
-- Todas las queries automáticamente filtran por ese tenant_id.
-- tenants NO tiene RLS — solo accesible con el rol superuser/admin.

ALTER TABLE phone_numbers   ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations   ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages        ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_config    ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge_docs  ENABLE ROW LEVEL SECURITY;
ALTER TABLE embeddings      ENABLE ROW LEVEL SECURITY;

-- Política: solo filas cuyo tenant_id coincide con la sesión actual
CREATE POLICY tenant_isolation ON phone_numbers
    USING (tenant_id = current_setting('app.current_tenant_id', true)::UUID);

CREATE POLICY tenant_isolation ON conversations
    USING (tenant_id = current_setting('app.current_tenant_id', true)::UUID);

CREATE POLICY tenant_isolation ON messages
    USING (tenant_id = current_setting('app.current_tenant_id', true)::UUID);

CREATE POLICY tenant_isolation ON agent_config
    USING (tenant_id = current_setting('app.current_tenant_id', true)::UUID);

CREATE POLICY tenant_isolation ON knowledge_docs
    USING (tenant_id = current_setting('app.current_tenant_id', true)::UUID);

CREATE POLICY tenant_isolation ON embeddings
    USING (tenant_id = current_setting('app.current_tenant_id', true)::UUID);


-- ════════════════════════════════════════════════════════════
-- Rol de aplicación (ejecutar como superuser en Railway)
-- ════════════════════════════════════════════════════════════
--
-- CREATE ROLE app_user LOGIN PASSWORD '<generar con openssl rand -hex 32>';
-- GRANT CONNECT ON DATABASE brain_omni TO app_user;
-- GRANT USAGE ON SCHEMA public TO app_user;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;
