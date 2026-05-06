"""LangGraph workflow skeleton."""

from multi_agent_research_lab.agents import AnalystAgent, ResearcherAgent, SupervisorAgent, WriterAgent
from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.state import ResearchState


class MultiAgentWorkflow:
    """Builds and runs the multi-agent graph.

    Keep orchestration here; keep agent internals in `agents/`.
    """

    def __init__(self) -> None:
        self._supervisor = SupervisorAgent()
        self._researcher = ResearcherAgent()
        self._analyst = AnalystAgent()
        self._writer = WriterAgent()

    def build(self) -> object:
        """Create an executable workflow object.

        The starter repo allows a simple in-process orchestration loop.
        """
        return self

    def run(self, state: ResearchState) -> ResearchState:
        """Execute the workflow and return final state."""
        settings = get_settings()

        while state.iteration < settings.max_iterations:
            self._supervisor.run(state)
            route = state.route_history[-1]
            try:
                if route == "researcher":
                    self._researcher.run(state)
                elif route == "analyst":
                    self._analyst.run(state)
                elif route == "writer":
                    self._writer.run(state)
                elif route == "done":
                    break
                else:
                    state.errors.append(f"Unknown route: {route}")
                    break
            except Exception as exc:
                state.errors.append(f"{route} failed: {exc}")
                state.add_trace_event("workflow.error", {"route": route, "error": str(exc)})
                if route == "writer":
                    break

        if not state.final_answer:
            state.final_answer = (
                "Workflow finished without a final answer. "
                "Check state.errors and trace for details."
            )
        return state
