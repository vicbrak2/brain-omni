"""Modelo de Scope y Canal para el ecosistema de agentes Brain Omni.

Cada agente tiene un Scope que define estrictamente qué acciones puede
ejecutar. El sistema tiene dos scopes:

    external  — Perfil de Público
                Interacción directa con clientes/seguidores.
                Puede: responder mensajes, buscar en KB, escalar.
                No puede: acceder a analíticas de todos los usuarios,
                           ver conversaciones de otros contactos.

    internal  — Perfil de Trabajador
                Asistencia operativa para el equipo.
                Puede: analizar datos agregados, generar reportes, sugerir.
                No puede: enviar mensajes a usuarios externos, escalar.

El canal identifica la plataforma (whatsapp | instagram | facebook | tiktok).
No todos los canales tienen ambos scopes activos (WA no tiene scope interno).
"""
from __future__ import annotations

from enum import Enum


class Scope(str, Enum):
    EXTERNAL = "external"   # Perfil de Público
    INTERNAL = "internal"   # Perfil de Trabajador


class Channel(str, Enum):
    WHATSAPP  = "whatsapp"
    INSTAGRAM = "instagram"
    FACEBOOK  = "facebook"
    TIKTOK    = "tiktok"


# ── Matriz de acciones permitidas por scope ────────────────────────────────────

# Acciones disponibles en el sistema
ACTIONS_EXTERNAL_ALLOWED = frozenset({
    "send_message",       # Enviar respuesta al usuario
    "search_kb",          # Buscar en knowledge base del tenant
    "escalate",           # Escalar a canal humano
    "get_faq",            # Obtener preguntas frecuentes del tenant
    "save_message",       # Guardar mensaje en historial
    "get_own_history",    # Historial de la conversación actual
})

ACTIONS_INTERNAL_ALLOWED = frozenset({
    "search_kb",          # Buscar en knowledge base del tenant
    "get_analytics",      # Métricas agregadas (mensajes/día, tokens, hits RAG)
    "get_all_convos",     # Ver historial de todas las conversaciones
    "generate_report",    # Generar reporte de actividad
    "suggest_content",    # Sugerir contenido/respuestas para el equipo
    "save_message",       # Guardar mensaje interno en historial
})

# Acciones explícitamente bloqueadas (redundancia para logs claros)
ACTIONS_EXTERNAL_BLOCKED = frozenset({
    "get_analytics",
    "get_all_convos",
    "generate_report",
})

ACTIONS_INTERNAL_BLOCKED = frozenset({
    "send_message",
    "escalate",
})

_ALLOWED: dict[Scope, frozenset[str]] = {
    Scope.EXTERNAL: ACTIONS_EXTERNAL_ALLOWED,
    Scope.INTERNAL: ACTIONS_INTERNAL_ALLOWED,
}


# ── Combinaciones agente → (canal, scope) ─────────────────────────────────────

class AgentIdentity:
    """Identidad completa de un agente en el ecosistema."""

    __slots__ = ("channel", "scope")

    def __init__(self, channel: Channel | str, scope: Scope | str) -> None:
        self.channel = Channel(channel)
        self.scope   = Scope(scope)

    @property
    def name(self) -> str:
        return f"{self.channel.value.title()}-{self.scope.value.title()}"

    def __repr__(self) -> str:
        return f"AgentIdentity(channel={self.channel.value!r}, scope={self.scope.value!r})"


# Agentes activos del ecosistema (para referencia y documentación)
ECOSYSTEM_AGENTS: list[AgentIdentity] = [
    AgentIdentity(Channel.WHATSAPP,  Scope.EXTERNAL),   # WA-Ext  → atención al cliente
    AgentIdentity(Channel.INSTAGRAM, Scope.EXTERNAL),   # IG-Ext  → moderación DMs
    AgentIdentity(Channel.FACEBOOK,  Scope.EXTERNAL),   # FB-Ext  → soporte Messenger
    AgentIdentity(Channel.TIKTOK,    Scope.EXTERNAL),   # TT-Ext  → moderación comentarios
    AgentIdentity(Channel.INSTAGRAM, Scope.INTERNAL),   # IG-Int  → análisis e inspiración
    AgentIdentity(Channel.FACEBOOK,  Scope.INTERNAL),   # FB-Int  → análisis de audiencia
    AgentIdentity(Channel.TIKTOK,    Scope.INTERNAL),   # TT-Int  → estrategia de contenido
]


# ── Enforcement ────────────────────────────────────────────────────────────────

class ScopeViolationError(PermissionError):
    """Raised cuando se intenta una acción fuera del scope del agente."""

    def __init__(self, action: str, scope: Scope, channel: Channel) -> None:
        self.action  = action
        self.scope   = scope
        self.channel = channel
        super().__init__(
            f"Acción '{action}' bloqueada para agente "
            f"{channel.value.upper()}-{scope.value.upper()}. "
            f"Scope '{scope.value}' no tiene permisos para esta operación."
        )


def check_action_allowed(action: str, scope: Scope | str, channel: Channel | str | None = None) -> None:
    """
    Verifica que `action` esté permitida para `scope`.

    Raises:
        ScopeViolationError: Si la acción está bloqueada para el scope dado.
    """
    scope_enum   = Scope(scope)
    channel_enum = Channel(channel) if channel else Channel.WHATSAPP

    allowed = _ALLOWED[scope_enum]
    if action not in allowed:
        raise ScopeViolationError(action, scope_enum, channel_enum)


def is_action_allowed(action: str, scope: Scope | str) -> bool:
    """Versión booleana de check_action_allowed (no lanza excepción)."""
    return action in _ALLOWED[Scope(scope)]
