# Fase 1 — MVP

#roadmap

**Proyecto:** [[00 - Index|Brain Omni]]

---

## Objetivo

Tener un agente funcional que atienda en al menos **un canal** y pueda responder preguntas frecuentes de un negocio real.

## Alcance

- [x] Definir stack tecnológico (Python / FastAPI / ARQ / Claude API / PostgreSQL)
- [x] Configurar el canal prioritario → [[WhatsApp]] (mayor alcance en pymes)
- [x] Implementar Gateway básico (webhook firmado, worker async ARQ)
- [x] Conectar con modelo de lenguaje (Claude API — multi-provider)
- [x] Base de datos de conversaciones (PostgreSQL + asyncpg, multi-tenant RLS)
- [x] Panel mínimo de administración (panel.html — tenants, prompts, docs)
- [ ] Pruebas con un negocio piloto real

## Estado actual — v0.4.0 (2026-08-17)

| Componente | Estado |
|---|---|
| WhatsApp Gateway + Worker | ✅ Deployado |
| Instagram Gateway + Worker | ✅ Deployado (webhook pendiente Meta) |
| Multi-tenant con RLS | ✅ |
| RAG con pgvector (384 dims) | ✅ v0.4.0 |
| Knowledge Base UI en panel | ✅ v0.4.0 |
| Negocio piloto activo | ⏳ Pendiente |

## Siguiente fase

[[Fase 2 — Expansión de Canales]]  
Integrar [[Facebook Messenger]], [[TikTok]], [[Chat Web]].  
Vista de conversaciones en panel · Métricas por tenant.

## Ver también

- [[Arquitectura]] · [[Agente Omnicanal]]
