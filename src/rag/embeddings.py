"""Embedding providers used by the RAG layer."""

from __future__ import annotations

import math
import re
from hashlib import sha256
from typing import Protocol

from openai import OpenAI


TOKEN_PATTERN = re.compile(r"[a-z0-9]{2,}")


class EmbeddingProvider(Protocol):
    model_name: str

    def embed(self, text: str) -> list[float]:
        """Embed a single text value."""

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of text values."""


class EmbeddingProviderError(RuntimeError):
    """Raised when embedding providers are misconfigured."""


class DeterministicEmbeddingModel:
    """Hash-based fallback for repeatable offline tests."""

    def __init__(self, *, dimensions: int = 96, model_name: str = "deterministic-hash-v1") -> None:
        self.dimensions = dimensions
        self.model_name = model_name

    def embed(self, text: str) -> list[float]:
        tokens = tokenize(text)
        vector = [0.0] * self.dimensions
        if not tokens:
            return vector

        for token in tokens:
            digest = sha256(token.encode("utf-8")).digest()
            slot = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            magnitude = 1.0 + (digest[5] / 255.0)
            vector[slot] += sign * magnitude

        return _normalize(vector)

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(text) for text in texts]


class OpenAIEmbeddingProvider:
    """OpenAI-backed embedding provider for production-style retrieval."""

    def __init__(
        self,
        *,
        api_key: str,
        model_name: str = "text-embedding-3-small",
    ) -> None:
        if not api_key.strip():
            raise EmbeddingProviderError("OPENAI_API_KEY is required for OpenAI embeddings")
        self.client = OpenAI(api_key=api_key)
        self.model_name = model_name
        self.dimensions: int | None = None

    def embed(self, text: str) -> list[float]:
        return self.embed_many([text])[0]

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        response = self.client.embeddings.create(
            model=self.model_name,
            input=texts,
        )
        vectors = [list(item.embedding) for item in response.data]
        if vectors:
            self.dimensions = len(vectors[0])
        return vectors


def build_embedding_provider(
    *,
    model_name: str,
    openai_api_key: str | None = None,
) -> EmbeddingProvider:
    if model_name.startswith("deterministic-"):
        return DeterministicEmbeddingModel(model_name=model_name)
    if openai_api_key:
        return OpenAIEmbeddingProvider(api_key=openai_api_key, model_name=model_name)
    raise EmbeddingProviderError(
        "A real embedding model was requested but OPENAI_API_KEY is missing. "
        "Set OPENAI_API_KEY or use EMBEDDING_MODEL=deterministic-hash-v1 for offline tests."
    )


def tokenize(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(text.lower())


def lexical_overlap(left: str, right: str) -> float:
    left_tokens = set(tokenize(left))
    right_tokens = set(tokenize(right))
    if not left_tokens or not right_tokens:
        return 0.0
    intersection = len(left_tokens & right_tokens)
    union = len(left_tokens | right_tokens)
    return intersection / union


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right:
        return 0.0
    return sum(a * b for a, b in zip(left, right, strict=False))


def combined_similarity(query: str, chunk_text: str, query_vector: list[float], chunk_vector: list[float]) -> float:
    dense_score = cosine_similarity(query_vector, chunk_vector)
    lexical_score = lexical_overlap(query, chunk_text)
    return round((0.8 * dense_score) + (0.2 * lexical_score), 6)


def _normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]
