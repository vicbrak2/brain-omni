#!/usr/bin/env python3
"""
update_vault.py — Actualiza checkboxes en el vault manual basándose en el
estado actual del código fuente. Los items que dependen de configuración
externa (Meta, piloto real) se dejan como False y deben marcarse a mano.

Uso: python tools/update_vault.py
"""

import re
from pathlib import Path

ROOT = Path(__file__).parent.parent  # raíz del proyecto


# ── Helpers ───────────────────────────────────────────────────────────────────

def has_file(*paths: str) -> bool:
    """True si existe al menos uno de los paths dados."""
    return any((ROOT / p).exists() for p in paths)


def file_contains(path: str, pattern: str) -> bool:
    """True si el archivo existe y contiene el patrón regex."""
    p = ROOT / path
    if not p.exists():
        return False
    return bool(re.search(pattern, p.read_text(encoding="utf-8", errors="ignore")))


def any_glob(pattern: str) -> bool:
    """True si algún archivo del proyecto coincide con el glob."""
    return any(ROOT.glob(pattern))


def set_checkbox(text: str, fragment: str, checked: bool) -> str:
    """
    Busca líneas con '- [ ] ...fragment...' o '- [x] ...fragment...'
    y actualiza la marca según `checked`.
    """
    mark = "x" if checked else " "
    escaped = re.escape(fragment)
    return re.sub(
        rf"(- \[)[ x](\] .*{escaped}.*)",
        lambda m: f"{m.group(1)}{mark}{m.group(2)}",
        text,
        flags=re.IGNORECASE,
    )


def update_file(md_path: Path, checks: list[tuple[str, bool]]) -> bool:
    if not md_path.exists():
        print(f"  ⚠️  No existe: {md_path}")
        return False

    text = md_path.read_text(encoding="utf-8")
    original = text

    for fragment, checked in checks:
        text = set_checkbox(text, fragment, checked)

    if text != original:
        md_path.write_text(text, encoding="utf-8")
        print(f"  ✅ Actualizado: {md_path.name}")
        return True
    else:
        print(f"  — Sin cambios: {md_path.name}")
        return False


# ── Definición de checks ──────────────────────────────────────────────────────
#
# Convención:
#   True  → checkbox marcado automáticamente (código/archivo detectado)
#   False → debe marcarse a mano (ops externas, piloto real, etc.)

FASE1_CHECKS: list[tuple[str, bool]] = [
    # Stack: existe requirements.txt y FastAPI en él
    ("Definir stack tecnológico",
        has_file("requirements.txt") and
        file_contains("requirements.txt", r"fastapi")),

    # Canal WhatsApp: worker deployado
    ("Configurar el canal prioritario",
        has_file("app/workers/whatsapp.py")),

    # Gateway: ruta /whatsapp declarada en webhook.py
    # (el router ya está montado en /webhook por main.py)
    ("Implementar Gateway básico",
        file_contains("app/api/webhook.py", r'"/whatsapp"')),

    # LLM: cualquier módulo de llamada al modelo
    ("Conectar con modelo de lenguaje",
        has_file("app/core/claude.py", "app/core/brain.py")),

    # DB: repos de conversaciones + al menos una migración SQL
    ("Base de datos de conversaciones",
        has_file("app/db/repos/conversations.py") and
        any_glob("migrations/*.sql")),

    # Panel: HTML del panel existe
    ("Panel mínimo de administración",
        has_file("app/static/panel.html")),

    # ❌ Ops — no se puede detectar desde código
    ("Pruebas con un negocio piloto",
        False),
]

FASE2_CHECKS: list[tuple[str, bool]] = [
    # Instagram: worker + ruta webhook deployados
    # (Meta Business Portal config es ops → se marca sola cuando esté listo)
    ("Activar [[Instagram]]",
        has_file("app/workers/instagram.py") and
        file_contains("app/api/webhook.py", r"/webhook/instagram")),

    # Facebook Messenger: worker + sender deployados
    ("Facebook Messenger",
        has_file("app/workers/facebook.py") and
        has_file("app/core/facebook_sender.py")),

    # Vista de conversaciones: endpoint GET /tenants/{id}/conversations en admin
    ("Vista de conversaciones",
        file_contains("app/api/admin.py", r"conversations")),

    # Métricas: endpoint o módulo de métricas
    ("Métricas por tenant",
        file_contains("app/api/admin.py", r"metric|stats|metr") or
        has_file("app/core/metrics.py")),

    # Re-embedding: función específica de re-embed en admin o knowledge
    # (no confundir con delete_doc que hace cascade delete de chunks)
    ("Re-embedding automático",
        file_contains("app/api/admin.py", r"reembed|re_embed") or
        file_contains("app/db/repos/knowledge.py", r"async def.*reembed|re_embed")),

    # Rate-limit: middleware o configuración de throttling
    ("Throttling",
        has_file("app/core/throttle.py", "app/middleware/rate_limit.py") or
        file_contains("app/api/admin.py", r"throttl|rate.?limit|RateLim")),

    # Chat Web: worker o handler de chat web
    ("Chat Web",
        has_file("app/workers/chat_web.py", "app/workers/web.py",
                 "app/core/chat_web.py")),

    # TikTok: worker + sender deployados
    ("TikTok",
        has_file("app/workers/tiktok.py") and
        has_file("app/core/tiktok_sender.py")),
]


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    vault = ROOT / "vault"
    print("🔄 Actualizando checkboxes del vault...\n")

    changed = False
    changed |= update_file(
        vault / "roadmap" / "Fase 1 — MVP.md",
        FASE1_CHECKS,
    )
    changed |= update_file(
        vault / "roadmap" / "Fase 2 — Expansión de Canales.md",
        FASE2_CHECKS,
    )

    print("\n✅ Checkboxes actualizados" if changed else "\n— Vault ya al día")
