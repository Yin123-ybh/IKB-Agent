from __future__ import annotations

from ..models import SearchHit
from ..text_utils import tokenize


class LocalReranker:
    """BGE-Reranker compatible local fallback."""

    def rerank(self, query: str, hits: list[SearchHit]) -> list[SearchHit]:
        query_tokens = set(tokenize(query))
        if not query_tokens:
            return hits
        scored: list[tuple[float, SearchHit]] = []
        for hit in hits:
            content_tokens = set(tokenize(hit.content))
            lexical_bonus = len(query_tokens & content_tokens) / max(len(query_tokens), 1)
            hit.score = round(hit.score + lexical_bonus * 0.12, 5)
            scored.append((hit.score, hit))
        return [hit for _, hit in sorted(scored, key=lambda item: item[0], reverse=True)]

