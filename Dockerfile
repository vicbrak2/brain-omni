# syntax=docker/dockerfile:1
# Imagen unificada para API y worker — modo controlado por START_MODE

# ── Stage 1: dependencias ──────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

COPY requirements.txt .
RUN pip install --upgrade pip \
 && pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Stage 2: imagen final ──────────────────────────────────────────────────
FROM python:3.12-slim

# Usuario no-root
RUN addgroup --system app && adduser --system --ingroup app app

WORKDIR /app

# Copiar dependencias del stage builder
COPY --from=builder /install /usr/local

# Copiar código fuente
COPY --chown=app:app . .

USER app

# START_MODE=api  → uvicorn (API service, default)
# START_MODE=worker → arq worker
ENV START_MODE=api
ENV PORT=8080
EXPOSE 8080

CMD ["sh", "-c", \
  "if [ \"$START_MODE\" = \"worker\" ]; then \n\
    arq app.workers.whatsapp.WorkerSettings; \n\
  else \n\
    uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1; \n\
  fi"]
