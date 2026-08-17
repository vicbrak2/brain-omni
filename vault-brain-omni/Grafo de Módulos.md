---
tags: [dag, arquitectura]
proyecto: brain-omni
---

# Grafo de Módulos

**Proyecto:** [[00 - brain-omni Index|brain-omni]]  
#dag

Abre la **Vista de Grafo** en Obsidian para ver la red.

## Módulos (38)

- [[app.__init__]] `app` — 0 dep(s)
- [[api.__init__]] `app.api` — 0 dep(s)
- [[api.admin]] `app.api` — 5 dep(s)
- [[webhook]] `app.api` — 1 dep(s)
- [[core.__init__]] `app.core` — 0 dep(s)
- [[agent_prompts]] `app.core` — 1 dep(s)
- [[brain]] `app.core` — 1 dep(s)
- [[claude]] `app.core` — 2 dep(s)
- [[config]] `app.core` — 0 dep(s)
- [[embeddings]] `app.core` — 1 dep(s)
- [[facebook_sender]] `app.core` — 1 dep(s)
- [[instagram_sender]] `app.core` — 1 dep(s)
- [[providers]] `app.core` — 0 dep(s)
- [[scope]] `app.core` — 0 dep(s)
- [[tiktok_sender]] `app.core` — 1 dep(s)
- [[whatsapp_sender]] `app.core` — 1 dep(s)
- [[db.__init__]] `app.db` — 0 dep(s)
- [[connection]] `app.db` — 1 dep(s)
- [[models]] `app.db` — 0 dep(s)
- [[repos.__init__]] `app.db.repos` — 0 dep(s)
- [[repos.admin]] `app.db.repos` — 0 dep(s)
- [[agent_configs]] `app.db.repos` — 0 dep(s)
- [[conversations]] `app.db.repos` — 0 dep(s)
- [[knowledge]] `app.db.repos` — 0 dep(s)
- [[messages]] `app.db.repos` — 0 dep(s)
- [[tenants]] `app.db.repos` — 0 dep(s)
- [[workers.__init__]] `app.workers` — 0 dep(s)
- [[facebook]] `app.workers` — 10 dep(s)
- [[instagram]] `app.workers` — 8 dep(s)
- [[settings]] `app.workers` — 5 dep(s)
- [[tiktok]] `app.workers` — 10 dep(s)
- [[whatsapp]] `app.workers` — 9 dep(s)
- [[tests.__init__]] `tests` — 0 dep(s)
- [[conftest]] `tests` — 0 dep(s)
- [[test_parsers]] `tests` — 2 dep(s)
- [[test_signature]] `tests` — 1 dep(s)
- [[auditor]] `tools` — 0 dep(s)
- [[update_vault]] `tools` — 0 dep(s)
