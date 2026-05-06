from multi_agent_research_lab.observability.tracing import trace_span


def test_trace_span_records_duration() -> None:
    with trace_span("test-span", {"k": "v"}) as span:
        assert span["name"] == "test-span"
        assert span["attributes"]["k"] == "v"
    assert isinstance(span["duration_seconds"], float)
    assert span["duration_seconds"] >= 0
