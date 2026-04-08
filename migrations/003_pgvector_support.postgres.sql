CREATE EXTENSION IF NOT EXISTS vector;

ALTER TABLE knowledge_chunk_embeddings
ADD COLUMN IF NOT EXISTS embedding_vector vector(1536);

UPDATE knowledge_chunk_embeddings
SET embedding_vector = embedding::vector
WHERE embedding_vector IS NULL
  AND embedding_model = 'text-embedding-3-small'
  AND embedding_dimensions = 1536;
