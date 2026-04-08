ALTER TABLE knowledge_documents ADD COLUMN valid_from TIMESTAMP NULL;
ALTER TABLE knowledge_documents ADD COLUMN valid_to TIMESTAMP NULL;
ALTER TABLE knowledge_documents ADD COLUMN content_hash VARCHAR(64) NULL;
ALTER TABLE knowledge_documents ADD COLUMN updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE knowledge_documents ADD COLUMN source_path TEXT NULL;

ALTER TABLE knowledge_chunks ADD COLUMN source VARCHAR(128) NULL;
ALTER TABLE knowledge_chunks ADD COLUMN document_type VARCHAR(128) NULL;
ALTER TABLE knowledge_chunks ADD COLUMN version VARCHAR(64) NULL;
ALTER TABLE knowledge_chunks ADD COLUMN team VARCHAR(128) NULL;
ALTER TABLE knowledge_chunks ADD COLUMN valid_from TIMESTAMP NULL;
ALTER TABLE knowledge_chunks ADD COLUMN valid_to TIMESTAMP NULL;
ALTER TABLE knowledge_chunks ADD COLUMN content_hash VARCHAR(64) NULL;
ALTER TABLE knowledge_chunks ADD COLUMN updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;

CREATE TABLE IF NOT EXISTS knowledge_chunk_embeddings (
    id INTEGER PRIMARY KEY,
    chunk_id VARCHAR(128) NOT NULL UNIQUE,
    embedding TEXT NOT NULL,
    embedding_model VARCHAR(128) NOT NULL,
    embedding_dimensions INTEGER NOT NULL,
    content_hash VARCHAR(64) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(chunk_id) REFERENCES knowledge_chunks(chunk_id)
);
CREATE INDEX IF NOT EXISTS idx_knowledge_chunk_embeddings_chunk_id ON knowledge_chunk_embeddings(chunk_id);

ALTER TABLE retrieval_events ADD COLUMN retrieval_status VARCHAR(64) NOT NULL DEFAULT 'ok';
ALTER TABLE retrieval_events ADD COLUMN scores TEXT NOT NULL DEFAULT '[]';
