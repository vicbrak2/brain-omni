-- Migración 004: ajustar embeddings para modelo HuggingFace gratuito
--
-- El schema original usaba VECTOR(1536) para text-embedding-3-small (OpenAI).
-- Cambiamos a VECTOR(384) para paraphrase-multilingual-MiniLM-L12-v2 (HF, gratis,
-- soporta español de forma nativa).
--
-- Como la tabla no tiene datos reales aún, la recreamos limpiamente.

DROP INDEX IF EXISTS idx_embeddings_vector;
DROP TABLE IF EXISTS embeddings;

CREATE TABLE embeddings (
    id          UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID         NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    doc_id      UUID         NOT NULL REFERENCES knowledge_docs(id) ON DELETE CASCADE,
    chunk_index INTEGER      NOT NULL DEFAULT 0,
    chunk_text  TEXT         NOT NULL,
    embedding   VECTOR(384),
    model       TEXT         NOT NULL DEFAULT 'paraphrase-multilingual-MiniLM-L12-v2',
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    UNIQUE(doc_id, chunk_index)
);

CREATE INDEX idx_embeddings_tenant ON embeddings(tenant_id);

-- Nota: índice vectorial se agrega cuando haya > 1000 filas.
-- Con pocos documentos el seq scan es suficiente.
