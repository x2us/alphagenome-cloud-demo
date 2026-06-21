"""Pluggable LLM backends for the Gödel Agent.

The agent never talks to a model directly; it goes through an ``LLMBackend``.
This keeps the recursive-self-improvement loop testable and lets the exact same
agent run with a real frontier model *or*, when no API key / network is
available (as in many CI / sandbox environments), with a deterministic
``StubBackend`` that mimics the *shape* of real model output well enough to
exercise the full pipeline — prompting, answer extraction and scoring.

Design note (relevant to the "Task 1 always scores 0" investigation):
a backend returns *raw text*. It is deliberately NOT the backend's job to
return a clean final answer. Turning raw text into a scoreable answer is the
job of :mod:`godel_agent.extract`, and that boundary is exactly where the
zero-score bug lives.
"""

from __future__ import annotations

import os
import re
from typing import Protocol


class LLMBackend(Protocol):
    """Anything that maps a prompt to raw completion text."""

    name: str

    def complete(self, prompt: str) -> str:  # pragma: no cover - protocol
        ...


class AnthropicBackend:
    """Real backend using the official ``anthropic`` SDK.

    Activates only when the SDK is importable *and* an API key is present.
    Reads ``ANTHROPIC_API_KEY`` (and honours ``ANTHROPIC_BASE_URL`` if the SDK
    does). Falls back is the caller's responsibility — see :func:`get_backend`.
    """

    name = "anthropic"

    def __init__(self, model: str = "claude-opus-4-8", max_tokens: int = 2048):
        import anthropic  # noqa: F401 - imported lazily on purpose

        self._client = anthropic.Anthropic()
        self._model = model
        self._max_tokens = max_tokens

    def complete(self, prompt: str) -> str:
        msg = self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        # Concatenate text blocks.
        return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")


class StubBackend:
    """Deterministic, offline backend.

    It does *not* try to be smart. For each track we encode the ground-truth
    answer inside the prompt (the harness passes it as a hidden ``[[gold:...]]``
    tag) and the stub echoes a realistic, model-style chain-of-thought ending
    in a natural-language answer line. This lets us reproduce, deterministically
    and without any network, the precise interaction between *model output
    format* and *answer extraction* that causes Task 1 to score 0.

    The point is NOT that the stub "knows" the answer — it is that real models
    also (often) produce the right answer but in a format the extractor fails to
    parse. The stub isolates the extraction bug from model capability.
    """

    name = "stub"

    # How the stub phrases its final answer per track. Crucially, NONE of these
    # use the ``\boxed{...}`` format that the buggy Track-1 extractor expects.
    _TEMPLATES = {
        "mgsm": "Let's reason step by step.\n{work}\nThe answer is {gold}.",
        "gpqa": "Let's analyse each option.\n{work}\nThe answer is ({gold}).",
        "game24": "Let me search for a valid expression.\n{work}\nAnswer: {gold}",
        "default": "{work}\nThe answer is {gold}.",
    }

    def complete(self, prompt: str) -> str:
        gold = self._extract_gold(prompt)
        track = self._extract_track(prompt)
        work = "(reasoning omitted for brevity)"
        template = self._TEMPLATES.get(track, self._TEMPLATES["default"])
        if gold is None:
            return work + "\nI am not sure."
        return template.format(work=work, gold=gold)

    @staticmethod
    def _extract_gold(prompt: str) -> str | None:
        m = re.search(r"\[\[gold:(.*?)\]\]", prompt, re.DOTALL)
        return m.group(1).strip() if m else None

    @staticmethod
    def _extract_track(prompt: str) -> str:
        m = re.search(r"\[\[track:(.*?)\]\]", prompt)
        return m.group(1).strip() if m else "default"


def get_backend(prefer: str | None = None) -> LLMBackend:
    """Return the best available backend.

    Order: explicit ``prefer`` -> Anthropic (if key + SDK) -> Stub.
    Set ``GODEL_BACKEND=stub`` to force offline mode.
    """
    prefer = prefer or os.environ.get("GODEL_BACKEND")
    if prefer == "stub":
        return StubBackend()
    if prefer in (None, "anthropic") and os.environ.get("ANTHROPIC_API_KEY"):
        try:
            return AnthropicBackend()
        except Exception:
            pass
    return StubBackend()
