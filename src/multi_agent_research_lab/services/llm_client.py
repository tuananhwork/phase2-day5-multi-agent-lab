"""LLM client abstraction.

Production note: agents should depend on this interface instead of importing an SDK directly.
"""

from dataclasses import dataclass

from tenacity import retry, stop_after_attempt, wait_fixed

from multi_agent_research_lab.core.config import get_settings


@dataclass(frozen=True)
class LLMResponse:
    content: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None


class LLMClient:
    """Provider-agnostic LLM client skeleton."""

    def __init__(self) -> None:
        settings = get_settings()
        self._model = settings.openai_model
        self._timeout_seconds = settings.timeout_seconds
        self._client = None
        try:
            from openai import OpenAI
        except Exception:
            OpenAI = None  # type: ignore[assignment]
        if OpenAI is not None:
            self._client = OpenAI(
                api_key=settings.openai_api_key or "local-router",
                base_url=settings.openai_base_url,
            )

    @retry(stop=stop_after_attempt(2), wait=wait_fixed(1), reraise=True)
    def _chat_completion(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        if self._client is None:
            raise RuntimeError("OpenAI SDK is not installed.")
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            timeout=self._timeout_seconds,
        )
        usage = response.usage
        content = response.choices[0].message.content or ""
        return LLMResponse(
            content=content,
            input_tokens=usage.prompt_tokens if usage else None,
            output_tokens=usage.completion_tokens if usage else None,
            cost_usd=self._estimate_cost(usage.prompt_tokens if usage else 0, usage.completion_tokens if usage else 0),
        )

    def complete(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        """Return a model completion."""
        try:
            return self._chat_completion(system_prompt=system_prompt, user_prompt=user_prompt)
        except Exception:
            fallback = self._fallback_text(user_prompt)
            pseudo_input_tokens = max(1, len(user_prompt) // 4)
            pseudo_output_tokens = max(1, len(fallback) // 4)
            return LLMResponse(
                content=fallback,
                input_tokens=pseudo_input_tokens,
                output_tokens=pseudo_output_tokens,
                cost_usd=self._estimate_cost(pseudo_input_tokens, pseudo_output_tokens),
            )

    def _fallback_text(self, user_prompt: str) -> str:
        preview = user_prompt.strip().splitlines()
        top = preview[0] if preview else "No prompt provided."
        return (
            "Offline fallback response.\n\n"
            "Summary:\n"
            f"- {top[:220]}\n"
            "- The local LLM endpoint was unavailable, so this synthetic answer keeps the workflow running.\n"
            "- Start the local router endpoint to get model-generated output."
        )

    def _estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        # Lightweight estimate for benchmarking only.
        return round((input_tokens * 0.00000015) + (output_tokens * 0.00000060), 6)
