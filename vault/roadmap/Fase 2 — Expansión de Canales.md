# Fase 2 — Expansión de Canales

#roadmap

**Proyecto:** [[00 - Index|Brain Omni]]

---

## Objetivo

Extender la cobertura a todos los canales planeados y añadir visibilidad operativa al panel de administración.

## Alcance

- [ ] Activar [[Instagram]] (configurar webhook en Meta Business Portal)
- [x] Implementar [[Facebook Messenger]] (gateway + worker)
- [ ] Vista de conversaciones en panel (historial por tenant)
- [ ] Métricas por tenant (mensajes/día, tokens, hits del RAG)
- [ ] Re-embedding automático al editar documentos de la knowledge base
- [ ] Throttling / rate-limit por tenant
- [ ] [[Chat Web]] — widget embebible para sitios externos
- [x] [[TikTok]] — comentarios (requiere TikTok for Business API)

## Dependencias

- Webhook de Instagram aprobado en Meta ([[Instagram]])
- Piloto activo con negocio real (datos reales para métricas)

## Anterior

[[Fase 1 — MVP]]

## Ver también

- [[Arquitectura]] · [[Agente Omnicanal]]
