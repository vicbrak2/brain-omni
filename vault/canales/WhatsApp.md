# WhatsApp

#canal

**Proyecto:** [[00 - Index|Brain Omni]]

---

## Integración

- API: **WhatsApp Business Cloud API** (Meta)
- Autenticación: token de acceso + verificación de webhook
- Formato de mensajes: JSON (texto, imagen, audio, botones)

## Webhook

```
POST /webhook/whatsapp
```

## Capacidades

- [ ] Mensajes de texto
- [ ] Mensajes de voz
- [ ] Imágenes
- [ ] Botones interactivos
- [ ] Listas

## Notas

- Requiere número de teléfono verificado como Business
- Límite de mensajes por segundo según tier de la cuenta

## Ver también

- [[Agente Omnicanal]] · [[Arquitectura]]
