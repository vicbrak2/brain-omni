-- Migración 003: índice parcial para upsert de configuración global del tenant
--
-- El UNIQUE(tenant_id, phone_number_id) existente no cubre correctamente
-- el caso phone_number_id IS NULL (PostgreSQL: NULL ≠ NULL en unique).
-- Este índice parcial permite ON CONFLICT (tenant_id) WHERE phone_number_id IS NULL.

CREATE UNIQUE INDEX IF NOT EXISTS idx_agent_config_global
    ON agent_config(tenant_id)
    WHERE phone_number_id IS NULL;
