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
    - 📄 `admin.py`
    - 📄 `webhook.py`
  - 📁 `core`
    - 📄 `__init__.py`
    - 📄 `brain.py`
    - 📄 `claude.py`
    - 📄 `config.py`
    - 📄 `embeddings.py`
    - 📄 `instagram_sender.py`
    - 📄 `providers.py`
    - 📄 `whatsapp_sender.py`
  - 📁 `db`
    - 📁 `repos`
      - 📄 `__init__.py`
      - 📄 `admin.py`
      - 📄 `conversations.py`
      - 📄 `knowledge.py`
      - 📄 `messages.py`
      - 📄 `tenants.py`
    - 📄 `__init__.py`
    - 📄 `connection.py`
    - 📄 `models.py`
  - 📁 `static`
    - 📄 `panel.html`
    - 📄 `status.html`
  - 📁 `workers`
    - 📄 `__init__.py`
    - 📄 `instagram.py`
    - 📄 `settings.py`
    - 📄 `whatsapp.py`
  - 📄 `__init__.py`
- 📁 `migrations`
  - 📄 `001_initial_schema.sql`
  - 📄 `002_instagram_accounts.sql`
  - 📄 `003_agent_config_index.sql`
  - 📄 `004_embeddings_384.sql`
- 📁 `tests`
  - 📄 `__init__.py`
  - 📄 `conftest.py`
  - 📄 `test_parsers.py`
  - 📄 `test_signature.py`
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
- 📁 `vault-brain-omni`
  - 📁 `módulos`
    - 📄 `__init__.md`
    - 📄 `brain.md`
    - 📄 `claude.md`
    - 📄 `config.md`
    - 📄 `connection.md`
    - 📄 `conversations.md`
    - 📄 `instagram.md`
    - 📄 `instagram_sender.md`
    - 📄 `messages.md`
    - 📄 `models.md`
    - 📄 `providers.md`
    - 📄 `settings.md`
    - 📄 `tenants.md`
    - 📄 `webhook.md`
    - 📄 `whatsapp.md`
    - 📄 `whatsapp_sender.md`
  - 📄 `00 - brain-omni Index.md`
  - 📄 `Estructura del Proyecto.md`
  - 📄 `Funcion Larga.md`
  - 📄 `Grafo de Módulos.md`
  - 📄 `Sin Tests.md`
  - 📄 `Todo Pendiente.md`
- 📄 `Dockerfile`
- 📄 `Dockerfile.worker`
- 📄 `main.py`
- 📄 `railway.toml`
- 📄 `README.md`
- 📄 `requirements-dev.txt`
- 📄 `requirements.txt`
