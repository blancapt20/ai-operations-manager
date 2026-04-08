# TODOs Not To Forget

DATASET:
- When the knowledge dataset is updated, trigger a rebuild or incremental refresh of the knowledge index so document chunks, embeddings, and related metadata stay in sync with the source files.
- Define the exact update strategy later: detect changed files, re-chunk only affected documents, regenerate embeddings only for changed chunks, and avoid a full rebuild when unnecessary.

RAG RESULTS:
- Improve RAG answer quality and ranking, especially for mixed-intent queries where semantically related but operationally wrong results can outrank the best support/refund match.
- Consider adding intent-aware boosting or filtering, for example boosting Customer Support and Operations for duplicate-charge and billing-error queries while down-ranking Claims unless the query explicitly signals chargeback, fraud, or bank dispute intent.
- Consider adding a reranking step on top of pgvector retrieval so the top-k candidates can be reordered with stronger semantic judgment before returning the final chunks.
- Consider adding query rewriting or normalization before retrieval so short ambiguous queries are expanded into clearer internal search intents.
- Consider adding document-type and team weighting so direct historical cases, refund SOPs, and complaint-handling guidance are prioritized more appropriately for support queries.
- Add a small retrieval evaluation benchmark with expected top results for representative queries such as duplicate charge, refund approval, complaint escalation, and password policy questions.

FROM INGESTION TO RAG:
- Rethink the per-ingestion query-building logic for RAG later; for now the pipeline uses the normalized subject/title as the retrieval query, but we should revisit whether email, tickets, internal events, and CLI JSON each need different query-construction rules.
