"""Brain: Orquestador de LLM multi-proveedor con rotación dinámica.

Portado de llm-virtual-brain/brain/core.py — versión mínima para brain-omni.
Solo incluye lo necesario: complete() + cadena de rotación + continuación automática.
"""
from __future__ import annotations

import asyncio
import json
import re
import time
from dataclasses import dataclass
from typing import Awaitable, Callable, Dict, List, Optional, Union

import httpx

from .providers import KNOWN_PROVIDERS, Provider, provider_from_dict

MAX_CONTINUATIONS = 3  # reintentos si el modelo corta por max_tokens

OnStep = Optional[Callable[[Dict], Awaitable[None]]]


class BrainError(Exception):
    """Error de orquestación del Brain."""


@dataclass
class Message:
    """Mensaje en la conversación LLM."""
    role: str   # "system" | "user" | "assistant"
    content: str

    def to_dict(self) -> Dict:
        return {"role": self.role, "content": self.content}


def provider_configured(provider: Provider) -> bool:
    """True si el provider tiene una API key real (no placeholder ni vacía)."""
    key = (provider.api_key or "").strip()
    if "${" in key:
        return False
    if not key and provider.name in KNOWN_PROVIDERS:
        return False
    return True


class Brain:
    """
    Orquestador LLM agnóstico: rota providers si uno falla, sticky index,
    y continúa automáticamente si la respuesta queda cortada por max_tokens.

    Uso mínimo:
        brain = Brain(providers=[...], app_name="whatsapp")
        text  = await brain.complete(messages)
    """

    def __init__(
        self,
        *,
        providers: Optional[List[Provider]] = None,
        timeout_seconds: int = 30,
        app_name: str = "brain_app",
    ):
        self.all_providers = providers or []
        self.providers = [p for p in self.all_providers if provider_configured(p)]
        self.skipped_providers = [p for p in self.all_providers if not provider_configured(p)]
        self.timeout_seconds = timeout_seconds
        self.app_name = app_name

        self._active_idx = 0
        self._last_used: Optional[str] = None

        if not self.all_providers:
            raise BrainError("Se requiere al menos un provider")
        if self.skipped_providers:
            names = ", ".join(p.name for p in self.skipped_providers)
            print(f"[brain:{app_name}] providers sin API key (omitidos): {names}")

    # ── API pública ─────────────────────────────────────────────────────────

    async def complete(
        self,
        messages: List[Union[Dict, Message]],
        max_tokens: int = 600,
        temperature: float = 0.2,
        on_step: OnStep = None,
    ) -> str:
        """Completa una conversación ya construida. Rota providers si alguno falla."""
        return await self._call_providers_chain(messages, max_tokens, temperature, on_step)

    def status(self) -> Dict:
        """Estado actual de la cadena de providers."""
        active = self._last_used or (
            self.providers[self._active_idx].name if self.providers else None
        )
        return {
            "app": self.app_name,
            "enabled": bool(self.providers),
            "active": active,
            "count": len(self.providers),
            "providers": [
                {"order": i, "name": p.name, "model": p.model}
                for i, p in enumerate(self.providers)
            ],
            "skipped": [
                {"name": p.name, "model": p.model, "reason": "sin API key"}
                for p in self.skipped_providers
            ],
        }

    # ── Internals ────────────────────────────────────────────────────────────

    async def _call_providers_chain(
        self,
        messages: List,
        max_tokens: int,
        temperature: float,
        on_step: OnStep = None,
    ) -> str:
        """Cadena con rotación dinámica y sticky index."""
        if not self.providers:
            faltantes = ", ".join(p.name for p in self.skipped_providers) or "ninguno definido"
            raise BrainError(
                f"Ningún provider tiene API key configurada (sin key: {faltantes}). "
                "Define OPENROUTER_API_KEY, CEREBRAS_API_KEY, HF_TOKEN o GROQ_API_KEY."
            )

        n = len(self.providers)
        errors: List[str] = []

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            for offset in range(n):
                idx = (self._active_idx + offset) % n
                provider = self.providers[idx]
                t0 = time.monotonic()
                await _emit(on_step, {
                    "provider": provider.name, "model": provider.model, "phase": "start",
                })
                try:
                    response, _trunc, _conts, _in, _out = await self._call_provider_complete(
                        client, provider, messages, max_tokens, temperature
                    )
                    if offset:
                        print(f"[brain:{self.app_name}] rotación → {provider.name} ({provider.model})")
                    self._active_idx = idx
                    self._last_used = provider.name
                    await _emit(on_step, {
                        "provider": provider.name, "model": provider.model, "phase": "done",
                        "ms": int((time.monotonic() - t0) * 1000),
                    })
                    return response
                except Exception as e:
                    body = ""
                    resp = getattr(e, "response", None)
                    if resp is not None:
                        try:
                            body = resp.text[:120]
                        except Exception:
                            pass
                    msg = f"{str(e)[:80]} {body}".strip()
                    errors.append(f"{provider.name}: {msg}")
                    await _emit(on_step, {
                        "provider": provider.name, "model": provider.model, "phase": "error",
                        "ms": int((time.monotonic() - t0) * 1000), "error": msg[:120],
                    })

        raise BrainError("Todos los providers fallaron · " + " | ".join(errors))

    async def _call_provider(
        self,
        client: httpx.AsyncClient,
        provider: Provider,
        messages: List,
        max_tokens: int,
        temperature: float,
    ) -> tuple:
        headers = provider.get_headers()
        payload = provider.get_payload(messages, max_tokens, temperature)

        try:
            r = await asyncio.wait_for(
                client.post(provider.url, headers=headers, json=payload),
                timeout=self.timeout_seconds,
            )
        except asyncio.TimeoutError:
            raise TimeoutError(
                f"{provider.name} no respondió en {self.timeout_seconds}s"
            )

        r.raise_for_status()
        response_json = r.json()
        content, truncated = provider.parse_response(response_json)
        if not content.strip():
            raise ValueError("respuesta vacía (sin content)")

        usage = response_json.get("usage", {})
        return (
            content,
            truncated,
            usage.get("prompt_tokens", 0),
            usage.get("completion_tokens", 0),
        )

    async def _call_provider_complete(
        self,
        client: httpx.AsyncClient,
        provider: Provider,
        messages: List,
        max_tokens: int,
        temperature: float,
    ) -> tuple:
        """Llama al provider y continúa si la respuesta quedó cortada (max_tokens)."""
        content, truncated, input_tokens, output_tokens = await self._call_provider(
            client, provider, messages, max_tokens, temperature
        )
        full = content
        total_in = input_tokens
        total_out = output_tokens
        convo = [
            m if isinstance(m, dict) else {"role": m.role, "content": m.content}
            for m in messages
        ]
        attempts = 0
        while truncated and attempts < MAX_CONTINUATIONS:
            attempts += 1
            convo = convo + [
                {"role": "assistant", "content": full},
                {"role": "user", "content": (
                    "Tu respuesta anterior quedó cortada por límite de longitud. "
                    "Continúa EXACTAMENTE donde quedaste, sin repetir nada de lo ya "
                    "escrito, sin reintroducciones ni comentarios sobre el corte."
                )},
            ]
            content, truncated, in_t, out_t = await self._call_provider(
                client, provider, convo, max_tokens, temperature
            )
            full += content
            total_in += in_t
            total_out += out_t
        return full, truncated, attempts, total_in, total_out


# ── Helpers ──────────────────────────────────────────────────────────────────

async def _emit(on_step: OnStep, event: Dict) -> None:
    """Dispara el callback de estado en vivo (best-effort, nunca rompe la cadena)."""
    if on_step is None:
        return
    try:
        await on_step(event)
    except Exception:
        pass


def extract_json(text: str) -> Optional[Dict]:
    """Extrae el primer objeto JSON de un texto (o None)."""
    try:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception:
        pass
    return None
