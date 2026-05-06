"""Writer agent skeleton."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.observability.tracing import trace_span
from multi_agent_research_lab.services.llm_client import LLMClient


class WriterAgent(BaseAgent):
    """Produces final answer from research and analysis notes."""

    name = "writer"

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self._llm = llm_client or LLMClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.final_answer`."""
        with trace_span("agent.writer", {"query": state.request.query}) as span:
            sources_text = "\n".join(
                [f"[{idx}] {doc.title} ({doc.url or 'no-url'})" for idx, doc in enumerate(state.sources, start=1)]
            )
            llm_response = self._llm.complete(
                system_prompt="You are a concise technical writer.",
                user_prompt=(
                    f"Write a clear answer for audience '{state.request.audience}'.\n"
                    "Use sections and include a short references list.\n\n"
                    f"Query:\n{state.request.query}\n\n"
                    f"Research Notes:\n{state.research_notes or ''}\n\n"
                    f"Analysis Notes:\n{state.analysis_notes or ''}\n\n"
                    f"Sources:\n{sources_text}"
                ),
            )
            state.final_answer = llm_response.content
            state.add_trace_event("agent.writer", span)
            state.agent_results.append(
                AgentResult(
                    agent=AgentName.WRITER,
                    content=state.final_answer,
                    metadata={
                        "input_tokens": llm_response.input_tokens,
                        "output_tokens": llm_response.output_tokens,
                        "cost_usd": llm_response.cost_usd,
                        "duration_seconds": span["duration_seconds"],
                    },
                )
            )
        return state
