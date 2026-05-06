"""Benchmark report rendering."""

from multi_agent_research_lab.core.schemas import BenchmarkMetrics


def render_markdown_report(metrics: list[BenchmarkMetrics]) -> str:
    """Render benchmark metrics to markdown."""

    lines = ["# Benchmark Report", "", "| Run | Latency (s) | Cost (USD) | Quality | Notes |", "|---|---:|---:|---:|---|"]
    for item in metrics:
        cost = "" if item.estimated_cost_usd is None else f"{item.estimated_cost_usd:.4f}"
        quality = "" if item.quality_score is None else f"{item.quality_score:.1f}"
        lines.append(f"| {item.run_name} | {item.latency_seconds:.2f} | {cost} | {quality} | {item.notes} |")
    lines.append("")
    lines.extend(_summary_lines(metrics))
    return "\n".join(lines) + "\n"


def _summary_lines(metrics: list[BenchmarkMetrics]) -> list[str]:
    if len(metrics) < 2:
        return ["## Summary", "", "Need at least two runs to compare baseline vs multi-agent."]
    baseline = next((m for m in metrics if "baseline" in m.run_name.lower()), metrics[0])
    other = next((m for m in metrics if m is not baseline), metrics[-1])
    quality_delta = (other.quality_score or 0.0) - (baseline.quality_score or 0.0)
    latency_delta = other.latency_seconds - baseline.latency_seconds
    cost_delta = (other.estimated_cost_usd or 0.0) - (baseline.estimated_cost_usd or 0.0)
    return [
        "## Summary",
        "",
        f"- Quality delta (`{other.run_name}` - `{baseline.run_name}`): {quality_delta:+.2f}",
        f"- Latency delta (`{other.run_name}` - `{baseline.run_name}`): {latency_delta:+.2f}s",
        f"- Cost delta (`{other.run_name}` - `{baseline.run_name}`): {cost_delta:+.4f} USD",
    ]
