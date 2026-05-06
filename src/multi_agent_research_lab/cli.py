"""Command-line entrypoint for the lab starter."""

from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel

from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.schemas import AgentName, AgentResult, ResearchQuery
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.evaluation.benchmark import run_benchmark
from multi_agent_research_lab.evaluation.report import render_markdown_report
from multi_agent_research_lab.graph.workflow import MultiAgentWorkflow
from multi_agent_research_lab.observability.logging import configure_logging
from multi_agent_research_lab.services.llm_client import LLMClient
from multi_agent_research_lab.services.storage import LocalArtifactStore

app = typer.Typer(help="Multi-Agent Research Lab starter CLI")
console = Console()


def _init() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)


@app.command()
def baseline(
    query: Annotated[str, typer.Option("--query", "-q", help="Research query")],
) -> None:
    """Run a single-agent baseline with one LLM call."""

    _init()
    state = _run_baseline_state(query=query)
    console.print(Panel.fit(state.final_answer, title="Single-Agent Baseline"))


@app.command("multi-agent")
def multi_agent(
    query: Annotated[str, typer.Option("--query", "-q", help="Research query")],
) -> None:
    """Run the multi-agent workflow skeleton."""

    _init()
    state = ResearchState(request=ResearchQuery(query=query))
    workflow = MultiAgentWorkflow()
    result = workflow.run(state)
    console.print(result.model_dump_json(indent=2))


@app.command()
def benchmark(
    query: Annotated[str, typer.Option("--query", "-q", help="Research query")],
) -> None:
    """Benchmark baseline vs multi-agent and save report artifacts."""
    _init()
    store = LocalArtifactStore()

    baseline_state, baseline_metrics = run_benchmark(
        run_name="baseline",
        query=query,
        runner=_run_baseline_state,
    )
    multi_state, multi_metrics = run_benchmark(
        run_name="multi-agent",
        query=query,
        runner=_run_multi_agent_state,
    )

    report = render_markdown_report([baseline_metrics, multi_metrics])
    report_path = store.write_text("benchmark_report.md", report)
    baseline_trace_path = store.write_text("traces/baseline_trace.json", baseline_state.model_dump_json(indent=2))
    multi_trace_path = store.write_text("traces/multi_agent_trace.json", multi_state.model_dump_json(indent=2))
    console.print(
        Panel.fit(
            (
                f"Saved benchmark report to: {report_path}\n"
                f"Saved baseline trace to: {baseline_trace_path}\n"
                f"Saved multi-agent trace to: {multi_trace_path}"
            ),
            title="Benchmark Complete",
        )
    )


def _run_baseline_state(query: str) -> ResearchState:
    request = ResearchQuery(query=query)
    state = ResearchState(request=request)
    llm = LLMClient()
    response = llm.complete(
        system_prompt="You are a helpful research assistant.",
        user_prompt=(
            f"Answer this research question for '{request.audience}'.\n"
            f"Question: {request.query}\n"
            "Be concise and include practical recommendations."
        ),
    )
    state.final_answer = response.content
    state.agent_results.append(
        AgentResult(
            agent=AgentName.WRITER,
            content=response.content,
            metadata={
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "cost_usd": response.cost_usd,
            },
        )
    )
    return state


def _run_multi_agent_state(query: str) -> ResearchState:
    workflow = MultiAgentWorkflow()
    state = ResearchState(request=ResearchQuery(query=query))
    return workflow.run(state)


if __name__ == "__main__":
    app()
