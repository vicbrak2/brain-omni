# Agente Omnicanal

#agente #ia

**Proyecto:** [[00 - Index|Brain Omni]]

---

## Responsabilidad

El agente recibe el mensaje normalizado, entiende el contexto de la conversación y genera una respuesta apropiada según el canal y el tipo de cliente.

## Flujo

1. Recibe mensaje unificado del Gateway
2. Recupera historial de la conversación
3. Llama al modelo de lenguaje con contexto
4. Devuelve respuesta al Dispatcher

## Canales que atiende

- [[WhatsApp]]
- [[Instagram]]
- [[Facebook Messenger]]
- [[TikTok]]
- [[Chat Web]]

## Ver también

- [[Arquitectura]]
