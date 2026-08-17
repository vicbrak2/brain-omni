-- Migración 005: agent_configs — configuración de agentes por canal y scope
--
-- Nuevo modelo de agentes que diferencia explícitamente:
--   • channel:  whatsapp | instagram | facebook | tiktok
--   • scope:    external  — interacción pública (clientes, seguidores)
--               internal  — operativo/analítico (equipo de trabajo)
--
-- La tabla COEXISTE con la tabla legacy `agent_config` (WA/IG backward compat).
-- Los workers nuevos (Facebook, TikTok) usan esta tabla exclusivamente.
-- Los workers legacy (WhatsApp, Instagram) seguirán usando agent_config
-- hasta que se migren voluntariamente.

CREATE TABLE IF NOT EXISTS agent_configs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    -- Canal de comunicación al que aplica esta configuración
    channel         TEXT NOT NULL CHECK (channel IN ('whatsapp', 'instagram', 'facebook', 'tiktok')),

    -- Scope del agente: external = público, internal = equipo
    scope           TEXT NOT NULL CHECK (scope IN ('external', 'internal')),

    -- Prompt del sistema; NULL = usar el template default del canal+scope
    system_prompt   TEXT,

    -- Parámetros de generación (NULL = defaults del Brain)
    temperature     REAL    CHECK (temperature BETWEEN 0 AND 1),
    max_tokens      INTEGER CHECK (max_tokens BETWEEN 50 AND 4096),

    -- Canal de escalación (solo relevante en scope=external)
    -- Ej: "whatsapp" para escalar a agente humano vía WA
    escalation_channel TEXT CHECK (escalation_channel IN ('whatsapp', 'instagram', 'facebook', 'tiktok', 'human')),

    -- Límite de mensajes antes de escalar (0 = sin escalación automática)
    escalation_after_msgs INTEGER NOT NULL DEFAULT 0,

    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Un tenant tiene como máximo una config por (canal, scope)
CREATE UNIQUE INDEX IF NOT EXISTS idx_agent_configs_tenant_channel_scope
    ON agent_configs (tenant_id, channel, scope);

-- Lookup rápido por tenant + canal (para workers que conocen el canal)
CREATE INDEX IF NOT EXISTS idx_agent_configs_tenant_channel
    ON agent_configs (tenant_id, channel)
    WHERE is_active = TRUE;

-- Trigger para actualizar updated_at automáticamente
CREATE OR REPLACE FUNCTION update_agent_configs_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_agent_configs_updated_at ON agent_configs;
CREATE TRIGGER trg_agent_configs_updated_at
    BEFORE UPDATE ON agent_configs
    FOR EACH ROW EXECUTE FUNCTION update_agent_configs_updated_at();

-- ── RLS ────────────────────────────────────────────────────────────────────────

ALTER TABLE agent_configs ENABLE ROW LEVEL SECURITY;

-- Lectura: el tenant sólo ve su propia config
CREATE POLICY agent_configs_tenant_read ON agent_configs
    FOR SELECT
    USING (tenant_id = current_setting('app.tenant_id', TRUE)::UUID);

-- Escritura: admin (no RLS) puede hacer todo; tenants sólo su fila
CREATE POLICY agent_configs_tenant_write ON agent_configs
    FOR ALL
    USING (tenant_id = current_setting('app.tenant_id', TRUE)::UUID);
