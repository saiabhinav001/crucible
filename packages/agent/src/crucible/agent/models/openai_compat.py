"""OpenAI-compatible model gateway — the real-model contract.

Works against any OpenAI-compatible chat-completions endpoint (a hosted provider
or a local open-weight server), which is the plan's local/dev fallback strategy.
It is deny-by-default: without a base URL and model it raises ModelNotConfigured
rather than silently degrading. The network call is provisioned in a real
environment (Phase 9/10); the prompt rendering and the strict-JSON parsing into
typed schemas are pure and unit-tested here.
"""

from __future__ import annotations

import json
from typing import Any

from crucible.agent import prompts
from crucible.agent.errors import ModelNotConfigured
from crucible.agent.ports import ModelRole, ModelUsage
from crucible.agent.schemas import AnalysisPlan, GeneratedCode
from crucible.agent.state import ColumnView


def parse_plan(content: str) -> AnalysisPlan:
    """Validate a model response into an AnalysisPlan. Untrusted until it fits
    the schema — a hallucinated shape raises and the graph retries then abstains."""
    return AnalysisPlan.model_validate(_loads(content))


def parse_code(content: str) -> GeneratedCode:
    return GeneratedCode.model_validate(_loads(content))


def _loads(content: str) -> dict[str, Any]:
    data = json.loads(content)
    if not isinstance(data, dict):
        raise ValueError("model response is not a JSON object")
    return data


class OpenAICompatModel:
    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        provider: str = "openai-compatible",
        temperature: float = 0.0,
    ) -> None:
        self._base_url = base_url
        self._api_key = api_key
        self._model = model
        self._provider = provider
        self._temperature = temperature

    @property
    def configured(self) -> bool:
        return bool(self._base_url and self._model)

    def manifest(self) -> dict[str, dict[str, Any]]:
        cfg = {
            "provider": self._provider,
            "model_id": self._model or "unconfigured",
            "prompt_version": prompts.PLANNER_PROMPT_VERSION,
            "policy_version": "static@1",
            "params": {"temperature": self._temperature},
        }
        return {
            role.value: dict(cfg) for role in (ModelRole.PLANNER, ModelRole.CODER, ModelRole.REPAIR)
        }

    async def plan(
        self, *, question: str, profile: list[ColumnView]
    ) -> tuple[AnalysisPlan, ModelUsage]:
        content, usage = await self._complete(prompts.render_planner(question, profile))
        return parse_plan(content), usage

    async def code(
        self, *, plan: AnalysisPlan, profile: list[ColumnView]
    ) -> tuple[GeneratedCode, ModelUsage]:
        prompt = prompts.render_coder(plan.model_dump_json(), profile)
        content, usage = await self._complete(prompt)
        return parse_code(content), usage

    async def repair(
        self, *, plan: AnalysisPlan, profile: list[ColumnView], prior_code: str, error: str
    ) -> tuple[GeneratedCode, ModelUsage]:
        content, usage = await self._complete(prompts.render_repair(prior_code, error))
        return parse_code(content), usage

    async def _complete(self, prompt: str) -> tuple[str, ModelUsage]:
        if not self.configured:
            raise ModelNotConfigured(
                "the OpenAI-compatible model requires base_url and model; no silent fallback"
            )
        # Provider integration (Phase 9/10): POST {base_url}/chat/completions with
        # response_format=json_object, temperature=self._temperature, and the
        # prompt as a single user message; return message content + token usage.
        raise ModelNotConfigured("OpenAI-compatible provider integration is not provisioned yet")
