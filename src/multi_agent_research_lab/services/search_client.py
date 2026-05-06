"""Search client abstraction for ResearcherAgent."""

from __future__ import annotations

from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.schemas import SourceDocument


class SearchClient:
    """Provider-agnostic search client skeleton."""

    def __init__(self) -> None:
        self._settings = get_settings()

    def search(self, query: str, max_results: int = 5) -> list[SourceDocument]:
        """Search for documents relevant to a query."""
        docs: list[SourceDocument]
        if self._settings.tavily_api_key:
            docs = self._search_tavily(query=query, max_results=max_results)
            if docs:
                return self._dedupe_and_trim(docs, max_results=max_results)
        docs = self._search_local_fallback(query=query)
        return self._dedupe_and_trim(docs, max_results=max_results)

    def _search_tavily(self, query: str, max_results: int) -> list[SourceDocument]:
        try:
            from tavily import TavilyClient  # type: ignore[import-not-found]
        except Exception:
            return []
        try:
            client = TavilyClient(api_key=self._settings.tavily_api_key)
            response = client.search(query=query, max_results=max_results)
            raw_results = response.get("results", [])
            docs: list[SourceDocument] = []
            for item in raw_results:
                docs.append(
                    SourceDocument(
                        title=item.get("title", "Untitled source"),
                        url=item.get("url"),
                        snippet=item.get("content", "")[:500],
                        metadata={"source": "tavily"},
                    )
                )
            return docs
        except Exception:
            return []

    def _search_local_fallback(self, query: str) -> list[SourceDocument]:
        return [
            SourceDocument(
                title=f"Background primer for: {query}",
                url="https://example.com/primer",
                snippet=(
                    f"This primer summarizes core concepts related to '{query}', "
                    "including architecture choices, common tradeoffs, and terminology."
                ),
                metadata={"source": "local-fallback"},
            ),
            SourceDocument(
                title=f"Implementation patterns for: {query}",
                url="https://example.com/patterns",
                snippet=(
                    f"This note outlines practical implementation patterns for '{query}', "
                    "covering orchestration, guardrails, and observability hooks."
                ),
                metadata={"source": "local-fallback"},
            ),
            SourceDocument(
                title=f"Evaluation checklist for: {query}",
                url="https://example.com/evaluation",
                snippet=(
                    f"This checklist provides quality and benchmarking criteria for '{query}', "
                    "with latency, cost, and output quality dimensions."
                ),
                metadata={"source": "local-fallback"},
            ),
        ]

    def _dedupe_and_trim(self, docs: list[SourceDocument], max_results: int) -> list[SourceDocument]:
        deduped: list[SourceDocument] = []
        seen: set[str] = set()
        for doc in docs:
            key = (doc.url or doc.title).strip().lower()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(
                SourceDocument(
                    title=doc.title.strip() or "Untitled source",
                    url=doc.url,
                    snippet=doc.snippet.strip()[:500],
                    metadata=doc.metadata,
                )
            )
            if len(deduped) >= max_results:
                break
        return deduped
