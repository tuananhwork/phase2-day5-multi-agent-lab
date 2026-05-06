"""Researcher agent skeleton."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.observability.tracing import trace_span
from multi_agent_research_lab.services.search_client import SearchClient


class ResearcherAgent(BaseAgent):
    """Collects sources and creates concise research notes."""

    name = "researcher"

    def __init__(self, search_client: SearchClient | None = None) -> None:
        self._search_client = search_client or SearchClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.sources` and `state.research_notes`."""
        with trace_span("agent.researcher", {"query": state.request.query}) as span:
            docs = self._search_client.search(
                query=state.request.query, max_results=state.request.max_sources
            )
            state.sources = docs
            note_lines = ["Research Notes:"]
            for idx, doc in enumerate(docs, start=1):
                note_lines.append(f"{idx}. {doc.title}: {doc.snippet}")
            state.research_notes = "\n".join(note_lines)

            span["attributes"]["sources_count"] = len(docs)
            span["attributes"]["source_titles"] = [d.title for d in docs[:5]]
            span["attributes"]["source_urls"] = [d.url for d in docs[:5]]
            span["attributes"]["research_notes_preview"] = state.research_notes[:500]
            state.add_trace_event("agent.researcher", span)
            state.agent_results.append(
                AgentResult(
                    agent=AgentName.RESEARCHER,
                    content=state.research_notes,
                    metadata={
                        "sources_count": len(docs),
                        "source_titles": [d.title for d in docs[:5]],
                        "duration_seconds": span["duration_seconds"],
                    },
                )
            )
        return state
