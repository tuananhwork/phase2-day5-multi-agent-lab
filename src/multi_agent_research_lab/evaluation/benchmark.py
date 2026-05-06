"""Benchmark skeleton for single-agent vs multi-agent."""

from time import perf_counter
from typing import Callable

from multi_agent_research_lab.core.schemas import BenchmarkMetrics
from multi_agent_research_lab.core.state import ResearchState


Runner = Callable[[str], ResearchState]


def run_benchmark(run_name: str, query: str, runner: Runner) -> tuple[ResearchState, BenchmarkMetrics]:
    """Measure latency and return benchmark metrics."""

    started = perf_counter()
    state = runner(query)
    latency = perf_counter() - started
    metrics = BenchmarkMetrics(
        run_name=run_name,
        latency_seconds=latency,
        estimated_cost_usd=_sum_cost(state),
        quality_score=_quality_score(state),
        notes=_build_notes(state),
    )
    return state, metrics


def _sum_cost(state: ResearchState) -> float:
    total = 0.0
    for result in state.agent_results:
        raw_cost = result.metadata.get("cost_usd")
        if isinstance(raw_cost, int | float):
            total += float(raw_cost)
    return round(total, 6)


def _quality_score(state: ResearchState) -> float:
    score = 0.0
    if state.research_notes:
        score += 2.5
    if state.analysis_notes:
        score += 2.5
    if state.final_answer and len(state.final_answer) > 120:
        score += 3.0
    if state.sources:
        score += 1.0
    if "reference" in (state.final_answer or "").lower() or "[" in (state.final_answer or ""):
        score += 1.0
    if state.errors:
        score -= min(2.0, len(state.errors) * 0.5)
    return max(0.0, min(10.0, score))


def _build_notes(state: ResearchState) -> str:
    return (
        f"iterations={state.iteration}; "
        f"sources={len(state.sources)}; "
        f"errors={len(state.errors)}"
    )
