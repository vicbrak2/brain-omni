---
tags: [estructura, auditoria]
proyecto: brain-omni
---

# Estructura del Proyecto

**Proyecto:** [[00 - brain-omni Index|brain-omni]]  
#estructura

## Árbol

- 📁 `app`
  - 📁 `api`
    - 📄 `__init__.py`
    - 📄 `webhook.py`
  - 📁 `core`
    - 📄 `__init__.py`
    - 📄 `brain.py`
    - 📄 `claude.py`
    - 📄 `config.py`
    - 📄 `instagram_sender.py`
    - 📄 `providers.py`
    - 📄 `whatsapp_sender.py`
  - 📁 `db`
    - 📁 `repos`
      - 📄 `__init__.py`
      - 📄 `conversations.py`
      - 📄 `messages.py`
      - 📄 `tenants.py`
    - 📄 `__init__.py`
    - 📄 `connection.py`
    - 📄 `models.py`
  - 📁 `workers`
    - 📄 `__init__.py`
    - 📄 `instagram.py`
    - 📄 `settings.py`
    - 📄 `whatsapp.py`
  - 📄 `__init__.py`
- 📁 `migrations`
  - 📄 `001_initial_schema.sql`
  - 📄 `002_instagram_accounts.sql`
- 📁 `vault`
  - 📁 `canales`
    - 📄 `Chat Web.md`
    - 📄 `Facebook Messenger.md`
    - 📄 `Instagram.md`
    - 📄 `TikTok.md`
    - 📄 `WhatsApp.md`
  - 📁 `roadmap`
    - 📄 `Fase 1 — MVP.md`
  - 📄 `00 - Index.md`
  - 📄 `Agente Omnicanal.md`
  - 📄 `Arquitectura.md`
- 📄 `Dockerfile`
- 📄 `Dockerfile.worker`
- 📄 `main.py`
- 📄 `railway.toml`
- 📄 `README.md`
- 📄 `requirements.txt`
