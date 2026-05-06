"""Analyst agent skeleton."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.observability.tracing import trace_span
from multi_agent_research_lab.services.llm_client import LLMClient


class AnalystAgent(BaseAgent):
    """Turns research notes into structured insights."""

    name = "analyst"

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self._llm = llm_client or LLMClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.analysis_notes`."""
        with trace_span(
            "agent.analyst",
            {
                "query": state.request.query,
                "research_notes_length": len(state.research_notes or ""),
            },
        ) as span:
            prompt = (
                "Analyze the research notes. Return sections: Key Claims, Agreement/Disagreement, "
                "Evidence Gaps, and Confidence."
            )
            user_prompt = f"Query: {state.request.query}\n\nNotes:\n{state.research_notes or ''}\n\n{prompt}"
            llm_response = self._llm.complete(
                system_prompt="You are a rigorous research analyst.",
                user_prompt=user_prompt,
            )
            state.analysis_notes = llm_response.content
            span["attributes"]["system_prompt"] = "You are a rigorous research analyst."
            span["attributes"]["user_prompt_preview"] = user_prompt[:500]
            span["attributes"]["analysis_notes_preview"] = state.analysis_notes[:500]
            span["attributes"]["input_tokens"] = llm_response.input_tokens
            span["attributes"]["output_tokens"] = llm_response.output_tokens
            span["attributes"]["cost_usd"] = llm_response.cost_usd
            state.add_trace_event("agent.analyst", span)
            state.agent_results.append(
                AgentResult(
                    agent=AgentName.ANALYST,
                    content=state.analysis_notes,
                    metadata={
                        "input_tokens": llm_response.input_tokens,
                        "output_tokens": llm_response.output_tokens,
                        "cost_usd": llm_response.cost_usd,
                        "duration_seconds": span["duration_seconds"],
                    },
                )
            )
        return state
