"""Supervisor / router skeleton."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.observability.tracing import trace_span


class SupervisorAgent(BaseAgent):
    """Decides which worker should run next and when to stop."""

    name = "supervisor"

    def run(self, state: ResearchState) -> ResearchState:
        """Update `state.route_history` with the next route."""
        settings = get_settings()
        with trace_span(
            "agent.supervisor",
            {
                "query": state.request.query,
                "iteration_before": state.iteration,
                "has_research_notes": bool(state.research_notes),
                "has_analysis_notes": bool(state.analysis_notes),
                "has_final_answer": bool(state.final_answer),
            },
        ) as span:
            if state.iteration >= settings.max_iterations:
                next_route = "done"
                reason = "max_iterations_reached"
            elif not state.research_notes:
                next_route = "researcher"
                reason = "missing_research_notes"
            elif not state.analysis_notes:
                next_route = "analyst"
                reason = "missing_analysis_notes"
            elif not state.final_answer:
                next_route = "writer"
                reason = "missing_final_answer"
            else:
                next_route = "done"
                reason = "all_required_fields_ready"

            state.record_route(next_route)
            span["attributes"]["route"] = next_route
            span["attributes"]["decision_reason"] = reason
            span["attributes"]["iteration_after"] = state.iteration
            state.add_trace_event("supervisor.route", {"next": next_route, "iteration": state.iteration})
            state.add_trace_event("agent.supervisor", span)
            state.agent_results.append(
                AgentResult(
                    agent=AgentName.SUPERVISOR,
                    content=f"Routed to '{next_route}' ({reason})",
                    metadata={"iteration": state.iteration, "reason": reason},
                )
            )
        return state
