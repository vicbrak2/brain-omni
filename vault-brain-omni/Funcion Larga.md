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

- 🟢 `app/workers/whatsapp.py:43` — `process_whatsapp_message` tiene 138 líneas (umbral 50)
- 🟢 `app/workers/instagram.py:70` — `process_instagram_message` tiene 133 líneas (umbral 50)
- 🟢 `app/core/brain.py:114` — `_call_providers_chain` tiene 55 líneas (umbral 50)
