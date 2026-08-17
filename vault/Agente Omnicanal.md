# Agente Omnicanal

#agente #ia

**Proyecto:** [[00 - Index|Brain Omni]]

---

## Responsabilidad

El agente recibe el mensaje normalizado, enriquece el contexto con la knowledge base del tenant (RAG) y genera una respuesta apropiada según el canal y el tipo de cliente.

## Flujo v0.4.0

1. Recibe mensaje unificado del Gateway (WhatsApp / Instagram)
2. Recupera historial de la conversación (PostgreSQL, multi-tenant RLS)
3. **RAG**: si el tenant tiene documentos, embebe la consulta y busca los 3 chunks más similares (pgvector cosine, umbral 0.35)
4. Construye el system prompt con contexto de negocio + bloque RAG
5. Llama al modelo de lenguaje (Claude API — multi-provider)
6. Guarda la respuesta y envía de vuelta al canal

## Canales activos

- [[WhatsApp]] ✅
- [[Instagram]] ✅ (webhook pendiente Meta)
- [[Facebook Messenger]] ⏳ Fase 2
- [[TikTok]] ⏳ Fase 2
- [[Chat Web]] ⏳ Fase 2

## Knowledge Base (RAG)

Cada tenant puede subir documentos (FAQ, políticas, productos) vía el panel de administración. El auditor fragmenta el contenido en chunks de 200 palabras, los embebe con HuggingFace (`paraphrase-multilingual-MiniLM-L12-v2`, 384 dims) y los almacena en `pgvector`.

## Ver también

- [[Arquitectura]]
