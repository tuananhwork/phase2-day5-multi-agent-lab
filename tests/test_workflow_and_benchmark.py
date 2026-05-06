from multi_agent_research_lab.core.schemas import ResearchQuery
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.evaluation.benchmark import run_benchmark
from multi_agent_research_lab.evaluation.report import render_markdown_report
from multi_agent_research_lab.graph.workflow import MultiAgentWorkflow


def test_workflow_produces_final_answer() -> None:
    state = ResearchState(request=ResearchQuery(query="How should we evaluate multi-agent systems?"))
    result = MultiAgentWorkflow().run(state)
    assert result.final_answer is not None
    assert len(result.route_history) >= 1


def test_benchmark_metrics_have_quality_and_cost() -> None:
    def _runner(query: str) -> ResearchState:
        state = ResearchState(request=ResearchQuery(query=query))
        state.research_notes = "notes"
        state.analysis_notes = "analysis"
        state.final_answer = "Final answer with [1] reference."
        return state

    _, metrics = run_benchmark("baseline", "query", _runner)
    assert metrics.quality_score is not None
    assert metrics.estimated_cost_usd is not None


def test_report_adds_summary() -> None:
    report = render_markdown_report(
        [
            run_benchmark("baseline", "query one", lambda q: ResearchState(request=ResearchQuery(query="hello world"), final_answer="a"))[1],
            run_benchmark("multi-agent", "query two", lambda q: ResearchState(request=ResearchQuery(query="hello world"), final_answer="b [1]", sources=[]))[1],
        ]
    )
    assert "## Summary" in report
