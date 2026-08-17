---
tags: [deuda-tecnica, auditoria]
proyecto: brain-omni
severidad: baja
---

# Funcion Larga

**Proyecto:** [[00 - brain-omni Index|brain-omni]]  
**Total:** 5 problema(s)  
#deuda-tecnica

## Detalle

- 🟢 `app/core/brain.py:114` — `_call_providers_chain` tiene 55 líneas (umbral 50)
- 🟢 `app/workers/whatsapp.py:43` — `process_whatsapp_message` tiene 138 líneas (umbral 50)
- 🟢 `app/workers/instagram.py:70` — `process_instagram_message` tiene 133 líneas (umbral 50)
- 🟢 `tools/auditor.py:193` — `build_import_graph` tiene 53 líneas (umbral 50)
- 🟢 `tools/auditor.py:607` — `generate_vault` tiene 103 líneas (umbral 50)
