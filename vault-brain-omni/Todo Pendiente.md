---
tags: [deuda-tecnica, auditoria]
proyecto: brain-omni
severidad: media
---

# Todo Pendiente

**Proyecto:** [[00 - brain-omni Index|brain-omni]]  
**Total:** 4 problema(s)  
#deuda-tecnica

## Detalle

- 🟡 `app/core/providers.py:64` — a veces dejan "content" vacío y ponen todo en "reasoning" — pero ese
- 🟡 `app/core/providers.py:78` — else "sin content (el modelo dejó todo en 'reasoning' interno, no es una respuesta)")
- 🟡 `app/core/providers.py:87` — # Alias retro-compatible: todo provider por defecto es OpenAI-compatible.
- 🟡 `app/core/providers.py:116` — # prompts largos gasta todo el max_tokens en "pensar" (content vacio) o
