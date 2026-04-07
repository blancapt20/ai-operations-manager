CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(64) PRIMARY KEY,
    applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS raw_events (
    id INTEGER PRIMARY KEY,
    ingested_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    source VARCHAR(64) NOT NULL,
    raw_payload TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_raw_events_source ON raw_events(source);
CREATE INDEX IF NOT EXISTS idx_raw_events_ingested_at ON raw_events(ingested_at);

CREATE TABLE IF NOT EXISTS normalized_events (
    id INTEGER PRIMARY KEY,
    event_id VARCHAR(128) NOT NULL UNIQUE,
    source VARCHAR(64) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    event_type VARCHAR(128) NOT NULL,
    body TEXT NOT NULL,
    subject TEXT NULL,
    customer_id VARCHAR(128) NULL,
    metadata TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_normalized_events_source ON normalized_events(source);
CREATE INDEX IF NOT EXISTS idx_normalized_events_event_type ON normalized_events(event_type);
CREATE INDEX IF NOT EXISTS idx_normalized_events_timestamp ON normalized_events(timestamp);

CREATE TABLE IF NOT EXISTS ingestion_metadata (
    id INTEGER PRIMARY KEY,
    logged_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    event_id VARCHAR(128) NOT NULL,
    source VARCHAR(64) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    event_type VARCHAR(128) NOT NULL,
    status VARCHAR(64) NOT NULL,
    message TEXT NULL
);
CREATE INDEX IF NOT EXISTS idx_ingestion_metadata_status ON ingestion_metadata(status);
CREATE INDEX IF NOT EXISTS idx_ingestion_metadata_event_id ON ingestion_metadata(event_id);
CREATE INDEX IF NOT EXISTS idx_ingestion_metadata_logged_at ON ingestion_metadata(logged_at);

CREATE TABLE IF NOT EXISTS cases (
    id INTEGER PRIMARY KEY,
    case_id VARCHAR(128) NOT NULL UNIQUE,
    event_id VARCHAR(128) NOT NULL,
    status VARCHAR(64) NOT NULL,
    classification VARCHAR(128) NULL,
    action VARCHAR(128) NULL,
    response_text TEXT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_cases_event_id ON cases(event_id);
CREATE INDEX IF NOT EXISTS idx_cases_status ON cases(status);

CREATE TABLE IF NOT EXISTS execution_trace_steps (
    id INTEGER PRIMARY KEY,
    case_id VARCHAR(128) NOT NULL,
    step_name VARCHAR(128) NOT NULL,
    status VARCHAR(64) NOT NULL,
    started_at TIMESTAMP NOT NULL,
    finished_at TIMESTAMP NOT NULL,
    latency_ms INTEGER NOT NULL,
    details TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_trace_case_id ON execution_trace_steps(case_id);
CREATE INDEX IF NOT EXISTS idx_trace_status ON execution_trace_steps(status);

CREATE TABLE IF NOT EXISTS knowledge_documents (
    id INTEGER PRIMARY KEY,
    document_id VARCHAR(128) NOT NULL UNIQUE,
    source VARCHAR(128) NOT NULL,
    document_type VARCHAR(128) NOT NULL,
    version VARCHAR(64) NULL,
    team VARCHAR(128) NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_knowledge_documents_source ON knowledge_documents(source);
CREATE INDEX IF NOT EXISTS idx_knowledge_documents_type ON knowledge_documents(document_type);

CREATE TABLE IF NOT EXISTS knowledge_chunks (
    id INTEGER PRIMARY KEY,
    chunk_id VARCHAR(128) NOT NULL UNIQUE,
    document_id VARCHAR(128) NOT NULL,
    chunk_index INTEGER NOT NULL,
    text TEXT NOT NULL,
    metadata TEXT NOT NULL DEFAULT '{}',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(document_id) REFERENCES knowledge_documents(document_id)
);
CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_document ON knowledge_chunks(document_id);

CREATE TABLE IF NOT EXISTS retrieval_events (
    id INTEGER PRIMARY KEY,
    case_id VARCHAR(128) NOT NULL,
    query_text TEXT NOT NULL,
    top_k INTEGER NOT NULL DEFAULT 5,
    retrieved_chunk_ids TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_retrieval_events_case ON retrieval_events(case_id);
