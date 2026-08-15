# Arquitectura

#arquitectura #tecnico

**Proyecto:** [[00 - Index|Brain Omni]]

---

## Visión general

Brain Omni actúa como un hub centralizado que recibe mensajes de múltiples canales, los procesa con un agente IA y responde de vuelta al canal de origen.

```
[WhatsApp]  ─┐
[Instagram] ─┤
[Facebook]  ─┼──► [Brain Omni API] ──► [Agente IA] ──► [Respuesta]
[TikTok]    ─┤
[Chat Web]  ─┘
```

## Componentes principales

| Componente | Descripción |
|---|---|
| **Gateway de canales** | Recibe webhooks de cada plataforma |
| **Normalizador** | Convierte mensajes a formato interno unificado |
| **Agente IA** | Procesa el mensaje y genera respuesta |
| **Dispatcher** | Envía la respuesta de vuelta al canal correcto |
| **Base de datos** | Historial de conversaciones por canal/usuario |

## Canales

→ [[WhatsApp]] · [[Instagram]] · [[Facebook Messenger]] · [[TikTok]] · [[Chat Web]]

## Agentes

→ [[Agente Omnicanal]]
