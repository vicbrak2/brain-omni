# Chat Web

#canal

**Proyecto:** [[00 - Index|Brain Omni]]

---

## Integración

- Protocolo: **WebSocket** (conexión persistente) o HTTP polling
- Widget embebible en cualquier sitio web
- Sin autenticación de terceros necesaria

## Endpoint

```
WS  /ws/chat
POST /api/chat/message
```

## Capacidades

- [ ] Mensajes de texto en tiempo real
- [ ] Indicador de escritura
- [ ] Historial de sesión
- [ ] Widget personalizable (colores, logo)

## Notas

- Canal más fácil de integrar y probar
- Ideal para comenzar el MVP
- El widget puede compartirse como script embebible (`<script>`)

## Ver también

- [[Agente Omnicanal]] · [[Arquitectura]]
