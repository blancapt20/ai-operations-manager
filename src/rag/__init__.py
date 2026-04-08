"""Retrieval and context assembly module package."""

from src.rag.embeddings import (
    DeterministicEmbeddingModel,
    OpenAIEmbeddingProvider,
    build_embedding_provider,
)
from src.rag.service import RetrievalService

__all__ = [
    "DeterministicEmbeddingModel",
    "OpenAIEmbeddingProvider",
    "RetrievalService",
    "build_embedding_provider",
]
