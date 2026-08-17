---
tags: [deuda-tecnica, auditoria]
proyecto: brain-omni
severidad: media
---

# Todo Pendiente

**Proyecto:** [[00 - brain-omni Index|brain-omni]]  
**Total:** 11 problema(s)  
#deuda-tecnica

## Detalle

- 🟡 `app/core/providers.py:64` — a veces dejan "content" vacío y ponen todo en "reasoning" — pero ese
- 🟡 `app/core/providers.py:78` — else "sin content (el modelo dejó todo en 'reasoning' interno, no es una respuesta)")
- 🟡 `app/core/providers.py:87` — # Alias retro-compatible: todo provider por defecto es OpenAI-compatible.
- 🟡 `app/core/providers.py:116` — # prompts largos gasta todo el max_tokens en "pensar" (content vacio) o
- 🟡 `app/core/agent_prompts.py:31` — # ── Header de scope (se antepone a TODO prompt del tenant) ───────────────────
- 🟡 `tools/auditor.py:33` — TODO_PATTERN = re.compile(r"\b(TODO|FIXME|HACK|XXX|BUG|TEMP)\b", re.IGNORECASE)
- 🟡 `tools/auditor.py:335` — issues.append({"tipo": "todo-pendiente", "severidad": "media",
- 🟡 `tools/auditor.py:509` — "todo-pendiente":    "deuda-tecnica",
- 🟡 `tools/auditor.py:513` — "async-bloqueante":  "async-bug",
- 🟡 `tools/auditor.py:727` — {"query": "tag:#async-bug",     "color": {"a": 1, "rgb": 16711680}},
- 🟡 `migrations/005_agent_configs.sql:74` — -- Escritura: admin (no RLS) puede hacer todo; tenants sólo su fila
