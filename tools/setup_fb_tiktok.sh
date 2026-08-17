#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# setup_fb_tiktok.sh — Configura Facebook Messenger y TikTok en producción
#
# Qué hace:
#   1. Verifica dependencias (railway CLI, psql)
#   2. Lee credenciales de forma interactiva (no las guarda en el historial)
#   3. Sube las variables de entorno a Railway
#   4. Corre migration 005 (agent_configs)
#   5. Crea tablas facebook_accounts y tiktok_accounts
#   6. Inserta los registros de cuenta para el tenant activo
#
# Uso en Termux:
#   cd ~/brain-omni
#   bash tools/setup_fb_tiktok.sh
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

# ── Colores ───────────────────────────────────────────────────────────────────
GRN='\033[0;32m'; YEL='\033[1;33m'; RED='\033[0;31m'; BLU='\033[0;34m'; NC='\033[0m'
ok()   { echo -e "${GRN}✅ $*${NC}"; }
warn() { echo -e "${YEL}⚠️  $*${NC}"; }
err()  { echo -e "${RED}❌ $*${NC}"; exit 1; }
step() { echo -e "\n${BLU}▶ $*${NC}"; }

# ── Banner ────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BLU}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${BLU}║   Brain Omni — Setup Facebook & TikTok v0.5     ║${NC}"
echo -e "${BLU}╚══════════════════════════════════════════════════╝${NC}"
echo ""

# ── 1. Verificar dependencias ─────────────────────────────────────────────────
step "Verificando dependencias..."

if ! command -v railway &>/dev/null; then
    warn "Railway CLI no encontrado. Instalando..."
    # Termux usa npm para instalar railway
    if command -v npm &>/dev/null; then
        npm install -g @railway/cli
        ok "Railway CLI instalado"
    else
        err "npm no encontrado. Instala Node.js primero: pkg install nodejs"
    fi
else
    ok "Railway CLI: $(railway --version 2>/dev/null || echo 'ok')"
fi

if ! command -v psql &>/dev/null; then
    warn "psql no encontrado. Instalando..."
    if command -v pkg &>/dev/null; then
        pkg install postgresql -y
        ok "psql instalado"
    else
        err "No se puede instalar psql automáticamente. Instala postgresql manualmente."
    fi
else
    ok "psql: $(psql --version | head -1)"
fi

# ── 2. Verificar login en Railway ─────────────────────────────────────────────
step "Verificando sesión Railway..."
if ! railway whoami &>/dev/null; then
    echo "No estás logueado en Railway. Abre este link en el navegador:"
    railway login --browserless 2>&1 | grep -E "https|code" || railway login
fi
ok "Sesión Railway activa"

# ── 3. Leer DATABASE_URL ──────────────────────────────────────────────────────
step "Obteniendo DATABASE_URL desde Railway..."

# Intenta obtenerla automáticamente del proyecto Railway vinculado
if DATABASE_URL=$(railway variables get DATABASE_URL 2>/dev/null) && [[ -n "$DATABASE_URL" ]]; then
    ok "DATABASE_URL obtenida automáticamente"
else
    warn "No se pudo obtener DATABASE_URL automáticamente"
    echo ""
    echo "Pégala desde Railway Dashboard → Variables:"
    echo -n "  DATABASE_URL: "
    read -r DATABASE_URL
    [[ -z "$DATABASE_URL" ]] && err "DATABASE_URL no puede estar vacía"
fi

# Verificar conexión a la DB
step "Verificando conexión a la base de datos..."
psql "$DATABASE_URL" -c "SELECT version();" -t --quiet | head -1 | sed 's/^ *//' \
    && ok "Conexión exitosa" \
    || err "No se pudo conectar a la DB. Verifica DATABASE_URL"

# ── 4. Leer credenciales Facebook ─────────────────────────────────────────────
step "Configuración de Facebook Messenger"
echo ""
echo "  Encuéntralas en: Meta Business Suite → Configuración → Configuración básica"
echo ""

echo -n "  FACEBOOK_ACCESS_TOKEN (Page Access Token): "
read -rs FACEBOOK_ACCESS_TOKEN; echo ""
[[ -z "$FACEBOOK_ACCESS_TOKEN" ]] && err "FACEBOOK_ACCESS_TOKEN requerido"

echo -n "  FACEBOOK_APP_SECRET (App Secret): "
read -rs FACEBOOK_APP_SECRET; echo ""
[[ -z "$FACEBOOK_APP_SECRET" ]] && err "FACEBOOK_APP_SECRET requerido"

echo -n "  FACEBOOK_VERIFY_TOKEN (elige uno, ej: brain_fb_verify_2025): "
read -r FACEBOOK_VERIFY_TOKEN
[[ -z "$FACEBOOK_VERIFY_TOKEN" ]] && FACEBOOK_VERIFY_TOKEN="brain_fb_verify_$(date +%s)"
echo "  → Usando: $FACEBOOK_VERIFY_TOKEN"

echo -n "  FACEBOOK_PAGE_ID (ID de tu Facebook Page, ej: 123456789): "
read -r FACEBOOK_PAGE_ID
[[ -z "$FACEBOOK_PAGE_ID" ]] && err "FACEBOOK_PAGE_ID requerido"

echo -n "  FACEBOOK_PAGE_NAME (nombre legible, ej: Mi Negocio): "
read -r FACEBOOK_PAGE_NAME
[[ -z "$FACEBOOK_PAGE_NAME" ]] && FACEBOOK_PAGE_NAME="Facebook Page"

# ── 5. Leer credenciales TikTok ───────────────────────────────────────────────
step "Configuración de TikTok for Business"
echo ""
echo "  Encuéntralas en: TikTok for Developers → Manage Apps → tu app"
echo "  (Si aún no tienes acceso al Comment Reply API, puedes dejar en blanco)"
echo ""

echo -n "  TIKTOK_ACCESS_TOKEN (Access Token, deja en blanco si no tienes aún): "
read -rs TIKTOK_ACCESS_TOKEN; echo ""

echo -n "  TIKTOK_APP_SECRET (App Secret / Client Secret): "
read -rs TIKTOK_APP_SECRET; echo ""

echo -n "  TIKTOK_CLIENT_KEY (Client Key / App ID): "
read -r TIKTOK_CLIENT_KEY

echo -n "  TIKTOK_USER_ID (ID de tu cuenta TikTok Business, ej: 7123456789): "
read -r TIKTOK_USER_ID

echo -n "  TIKTOK_USERNAME (@handle sin @, ej: minegocio): "
read -r TIKTOK_USERNAME
[[ -z "$TIKTOK_USERNAME" ]] && TIKTOK_USERNAME="tiktok_account"

# ── 6. Obtener tenant_id ──────────────────────────────────────────────────────
step "Obteniendo tenant activo..."
echo ""

TENANT_ID=$(psql "$DATABASE_URL" -t --quiet -c \
    "SELECT id FROM tenants WHERE is_active = TRUE ORDER BY created_at LIMIT 1;" \
    | tr -d '[:space:]')

if [[ -z "$TENANT_ID" ]]; then
    err "No se encontró ningún tenant activo en la DB"
fi

TENANT_NAME=$(psql "$DATABASE_URL" -t --quiet -c \
    "SELECT name FROM tenants WHERE id = '$TENANT_ID';" \
    | tr -d '[:space:]')

echo "  Tenant encontrado: $TENANT_NAME ($TENANT_ID)"
echo ""
echo -n "  ¿Es correcto? (s/N): "
read -r CONFIRM
[[ "$CONFIRM" != "s" && "$CONFIRM" != "S" ]] && err "Abortado. Edita manualmente si necesitas otro tenant."
ok "Tenant confirmado: $TENANT_NAME"

# ── 7. Subir variables a Railway ──────────────────────────────────────────────
step "Subiendo variables de entorno a Railway..."

railway variables set \
    "FACEBOOK_ACCESS_TOKEN=$FACEBOOK_ACCESS_TOKEN" \
    "FACEBOOK_APP_SECRET=$FACEBOOK_APP_SECRET" \
    "FACEBOOK_VERIFY_TOKEN=$FACEBOOK_VERIFY_TOKEN" \
    "FACEBOOK_PAGE_ID=$FACEBOOK_PAGE_ID"

ok "Variables de Facebook subidas"

if [[ -n "$TIKTOK_ACCESS_TOKEN" ]]; then
    railway variables set \
        "TIKTOK_ACCESS_TOKEN=$TIKTOK_ACCESS_TOKEN" \
        "TIKTOK_APP_SECRET=$TIKTOK_APP_SECRET" \
        "TIKTOK_CLIENT_KEY=$TIKTOK_CLIENT_KEY"
    ok "Variables de TikTok subidas"
else
    warn "TikTok access token vacío — variables no subidas (agrégalas luego con: railway variables set)"
fi

# ── 8. Correr migración 005 ───────────────────────────────────────────────────
step "Corriendo migración 005 (agent_configs)..."

psql "$DATABASE_URL" -f migrations/005_agent_configs.sql \
    && ok "Migración 005 completada" \
    || warn "La migración puede haber fallado o ya existía — continúa"

# ── 9. Crear tablas facebook_accounts y tiktok_accounts ──────────────────────
step "Creando tablas facebook_accounts y tiktok_accounts..."

psql "$DATABASE_URL" <<'SQL'
-- ── facebook_accounts ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS facebook_accounts (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID        NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    page_id     TEXT        NOT NULL,
    page_name   TEXT,
    is_active   BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_fb_page_id UNIQUE (page_id)
);
CREATE INDEX IF NOT EXISTS idx_fb_accounts_tenant ON facebook_accounts (tenant_id);

-- ── tiktok_accounts ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tiktok_accounts (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID        NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    tiktok_user_id  TEXT        NOT NULL,
    tiktok_username TEXT,
    is_active       BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_tt_user_id UNIQUE (tiktok_user_id)
);
CREATE INDEX IF NOT EXISTS idx_tt_accounts_tenant ON tiktok_accounts (tenant_id);

SELECT 'Tablas creadas/verificadas' AS status;
SQL

ok "Tablas listas"

# ── 10. Insertar registros de cuentas ─────────────────────────────────────────
step "Insertando registros de cuenta en la DB..."

# Facebook
psql "$DATABASE_URL" <<SQL
INSERT INTO facebook_accounts (tenant_id, page_id, page_name)
VALUES ('$TENANT_ID', '$FACEBOOK_PAGE_ID', '$FACEBOOK_PAGE_NAME')
ON CONFLICT (page_id) DO UPDATE
    SET page_name = EXCLUDED.page_name,
        tenant_id = EXCLUDED.tenant_id,
        updated_at = NOW();
SELECT 'facebook_accounts OK' AS status;
SQL
ok "facebook_accounts registrado"

# TikTok (solo si se proporcionó tiktok_user_id)
if [[ -n "$TIKTOK_USER_ID" ]]; then
    psql "$DATABASE_URL" <<SQL
INSERT INTO tiktok_accounts (tenant_id, tiktok_user_id, tiktok_username)
VALUES ('$TENANT_ID', '$TIKTOK_USER_ID', '$TIKTOK_USERNAME')
ON CONFLICT (tiktok_user_id) DO UPDATE
    SET tiktok_username = EXCLUDED.tiktok_username,
        tenant_id       = EXCLUDED.tenant_id,
        updated_at      = NOW();
SELECT 'tiktok_accounts OK' AS status;
SQL
    ok "tiktok_accounts registrado"
else
    warn "TikTok user_id vacío — no se insertó registro (agrégalo luego)"
fi

# ── 11. Resumen ────────────────────────────────────────────────────────────────
echo ""
echo -e "${GRN}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${GRN}║           ✅ Setup completado                    ║${NC}"
echo -e "${GRN}╚══════════════════════════════════════════════════╝${NC}"
echo ""
echo "  Tenant: $TENANT_NAME"
echo "  Facebook Page: $FACEBOOK_PAGE_NAME ($FACEBOOK_PAGE_ID)"
[[ -n "$TIKTOK_USER_ID" ]] && echo "  TikTok: @$TIKTOK_USERNAME ($TIKTOK_USER_ID)"
echo ""
echo -e "${YEL}Próximos pasos manuales:${NC}"
echo ""
echo "  1. FACEBOOK webhook — configura en Meta Business Portal:"
echo "     URL:   https://TU_DOMINIO/webhook/facebook"
echo "     Token: $FACEBOOK_VERIFY_TOKEN"
echo "     Suscríbete a: messages, messaging_postbacks"
echo ""
echo "  2. TIKTOK webhook (cuando tengas acceso al Comment Reply API):"
echo "     URL:   https://TU_DOMINIO/webhook/tiktok"
echo "     Suscríbete al evento: comment"
echo ""
echo "  3. Redeploy Railway para cargar las nuevas vars:"
echo "     railway up"
echo ""
