---
tags: [deuda-tecnica, auditoria]
proyecto: brain-omni
severidad: baja
---

# Funcion Larga

**Proyecto:** [[00 - brain-omni Index|brain-omni]]  
**Total:** 3 problema(s)  
#deuda-tecnica

## Detalle

- 🟢 `app/workers/whatsapp.py:41` — `process_whatsapp_message` tiene 98 líneas (umbral 50)
- 🟢 `app/workers/instagram.py:68` — `process_instagram_message` tiene 95 líneas (umbral 50)
- 🟢 `app/core/brain.py:114` — `_call_providers_chain` tiene 55 líneas (umbral 50)
