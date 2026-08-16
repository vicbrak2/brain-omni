-- Migración 002: tabla instagram_accounts
-- Registra las cuentas de Instagram Business por tenant.
-- Equivalente a phone_numbers pero para el canal de Instagram DMs.

CREATE TABLE IF NOT EXISTS instagram_accounts (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID        NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    ig_user_id      TEXT        NOT NULL,          -- ID de la cuenta IG Business (nuestra)
    ig_username     TEXT,                          -- @handle para logs legibles
    is_active       BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_ig_user_id UNIQUE (ig_user_id)
);

CREATE INDEX IF NOT EXISTS idx_ig_accounts_tenant ON instagram_accounts (tenant_id);

-- Trigger para updated_at automático
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_ig_accounts_updated_at
    BEFORE UPDATE ON instagram_accounts
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
