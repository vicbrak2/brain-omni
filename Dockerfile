# syntax=docker/dockerfile:1
# Imagen optimizada para Cloud Run (puerto 8080, non-root, multi-stage)

# ── Stage 1: dependencias ──────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

COPY requirements.txt .
RUN pip install --upgrade pip \
 && pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Stage 2: imagen final ──────────────────────────────────────────────────
FROM python:3.12-slim

# Usuario no-root (buena práctica en contenedores)
RUN addgroup --system app && adduser --system --ingroup app app

WORKDIR /app

# Copiar dependencias del stage builder
COPY --from=builder /install /usr/local

# Copiar código fuente
COPY --chown=app:app . .

USER app

# Cloud Run espera el servidor en el puerto $PORT (default 8080)
ENV PORT=8080
EXPOSE 8080

# Uvicorn en modo producción — 1 worker porque Cloud Run escala por instancias
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port $PORT --workers 1"]
