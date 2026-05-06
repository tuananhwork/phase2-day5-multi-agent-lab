"""Tracing hooks.

This file intentionally avoids binding to one provider. Students can plug in LangSmith,
Langfuse, OpenTelemetry, or simple JSON traces.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
import os
from time import perf_counter
from typing import Any

from multi_agent_research_lab.core.config import get_settings


@contextmanager
def trace_span(name: str, attributes: dict[str, Any] | None = None) -> Iterator[dict[str, Any]]:
    """Minimal span context with optional LangSmith export."""

    started = perf_counter()
    span: dict[str, Any] = {"name": name, "attributes": attributes or {}, "duration_seconds": None}
    langsmith_run = _start_langsmith_run(name=name, attributes=span["attributes"])
    try:
        yield span
    except Exception as exc:
        span["attributes"]["error"] = str(exc)
        _end_langsmith_run(langsmith_run, span=span, error=str(exc))
        raise
    finally:
        span["duration_seconds"] = perf_counter() - started
        if "error" not in span["attributes"]:
            _end_langsmith_run(langsmith_run, span=span, error=None)


def _start_langsmith_run(name: str, attributes: dict[str, Any]) -> Any | None:
    settings = get_settings()
    if not settings.langsmith_api_key:
        return None
    try:
        os.environ.setdefault("LANGSMITH_API_KEY", settings.langsmith_api_key)
        os.environ.setdefault("LANGSMITH_TRACING", "true")
        os.environ.setdefault("LANGSMITH_PROJECT", settings.langsmith_project)
        from langsmith.run_trees import RunTree  # type: ignore[import-not-found]

        run = RunTree(
            name=name,
            run_type="chain",
            inputs={"attributes": attributes},
            project_name=settings.langsmith_project,
        )
        run.post()
        return run
    except Exception:
        return None


def _end_langsmith_run(langsmith_run: Any | None, span: dict[str, Any], error: str | None) -> None:
    if langsmith_run is None:
        return
    try:
        if error:
            langsmith_run.end(error=error)
        else:
            langsmith_run.end(outputs={"span": span})
        langsmith_run.patch()
    except Exception:
        return
