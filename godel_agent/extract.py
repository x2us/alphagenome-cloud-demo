"""Answer extraction — the single most common cause of a benchmark track
scoring *exactly* zero while every other track scores normally.

This module ships TWO families of extractors on purpose:

* ``buggy_*``   — faithful reproductions of real, subtly-wrong extractors that
                  cause a whole track to score 0. These are what "Task 1 always
                  scores 0" looks like in practice.
* ``robust_*``  — the corrected versions.

Keeping both lets the harness *demonstrate* the failure and the fix, and lets
the Gödel Agent's ``self_update`` step swap a buggy extractor for a robust one
as a concrete, measurable self-improvement.

Why a parsing bug produces *exactly* zero (not "low") matters: if the extractor
returns ``None`` (or a value that can never match the gold format) for every
single item, the utility/accuracy is 0 for *all* candidate policies. The
self-improvement loop then sees a perfectly flat fitness landscape — every
rewrite scores 0 — so it gets no gradient and can never climb out. The bug is
upstream of reasoning ability entirely.
"""

from __future__ import annotations

import re
from typing import Optional

# --------------------------------------------------------------------------- #
# MGSM (Track 1): the answer is a single (possibly large) integer.            #
# --------------------------------------------------------------------------- #

# A real, real-world footgun: the harness was written for a model fine-tuned to
# emit ``\boxed{...}`` (MATH-style). The model used here instead writes
# "The answer is 42." / "答案是 42。" — so the boxed regex never matches and the
# extractor returns None for EVERY item -> Task 1 == 0/N, forever.
_BOXED_RE = re.compile(r"\\boxed\{([^}]*)\}")


def buggy_mgsm_extract(text: str) -> Optional[str]:
    """Buggy: only accepts ``\\boxed{...}``. Returns None otherwise."""
    m = _BOXED_RE.search(text)
    if not m:
        return None  # <-- this single line zeroes out the whole track
    return _normalize_int(m.group(1))


# A second, equally common buggy variant kept for the diagnosis writeup:
# "grab the FIRST number in the text". In chain-of-thought answers the first
# number is almost always an intermediate quantity from the problem, so this
# scores near-zero too (kept here to show it is a *family* of bugs).
_FIRST_NUM_RE = re.compile(r"-?\d[\d,]*")


def buggy_first_number_extract(text: str) -> Optional[str]:
    m = _FIRST_NUM_RE.search(text)
    return _normalize_int(m.group(0)) if m else None


# Multilingual answer cues (MGSM covers en, zh, ja, de, fr, ru, es, ...).
_ANSWER_CUES = re.compile(
    r"(?:the\s+answer\s+is|answer\s*[:：]|答案是|答案[:：]|答え(?:は)?|réponse|respuesta|antwort|ответ|####)\s*",
    re.IGNORECASE,
)


def robust_mgsm_extract(text: str) -> Optional[str]:
    """Robust: prefer an explicit answer cue; else take the LAST number.

    Handles thousands separators, trailing punctuation, and multilingual cues.
    Taking the last number is correct for chain-of-thought, where the final
    line states the result.
    """
    # 1) Explicit cue ("the answer is X", "答案是 X", GSM8K "#### X").
    cue = list(_ANSWER_CUES.finditer(text))
    search_space = text[cue[-1].end():] if cue else text
    nums = _FIRST_NUM_RE.findall(search_space)
    if not nums:
        nums = _FIRST_NUM_RE.findall(text)  # fall back to whole text
    if not nums:
        return None
    return _normalize_int(nums[-1] if cue else nums[-1])


def _normalize_int(raw: str) -> Optional[str]:
    raw = raw.strip().replace(",", "").replace(" ", "")
    raw = raw.rstrip(".。")
    m = re.search(r"-?\d+", raw)
    return str(int(m.group(0))) if m else None


# --------------------------------------------------------------------------- #
# GPQA (Track 2): answer is a multiple-choice letter A-D.                     #
# --------------------------------------------------------------------------- #

_LETTER_RE = re.compile(r"\(?\s*([A-D])\s*\)?", re.IGNORECASE)
_GPQA_CUE = re.compile(r"(?:the\s+answer\s+is|answer\s*[:：]|答案是|####)\s*", re.IGNORECASE)


def robust_gpqa_extract(text: str) -> Optional[str]:
    cue = list(_GPQA_CUE.finditer(text))
    space = text[cue[-1].end():] if cue else text
    m = _LETTER_RE.search(space)
    if not m and not cue:
        # last-resort: last standalone letter in the text
        all_letters = re.findall(r"\b([A-D])\b", text)
        return all_letters[-1].upper() if all_letters else None
    return m.group(1).upper() if m else None


# --------------------------------------------------------------------------- #
# Game of 24 (Track 3): answer is an arithmetic expression evaluating to 24.  #
# --------------------------------------------------------------------------- #

_EXPR_RE = re.compile(r"[0-9+\-*/() ]{5,}")
_GAME24_CUE = re.compile(r"(?:answer\s*[:：]|the\s+answer\s+is|expression\s*[:：])\s*", re.IGNORECASE)


def robust_game24_extract(text: str) -> Optional[str]:
    cue = list(_GAME24_CUE.finditer(text))
    space = text[cue[-1].end():] if cue else text
    candidates = _EXPR_RE.findall(space) or _EXPR_RE.findall(text)
    # Choose the last expression that actually contains an operator.
    for expr in reversed(candidates):
        if any(op in expr for op in "+-*/"):
            return expr.strip()
    return None


# Registry the harness / agent use to look up an extractor by name. The Gödel
# Agent rewrites THIS mapping (cheaply, at runtime) as a self-improvement.
EXTRACTORS = {
    # Track 1 ships BROKEN on purpose to reproduce the zero-score report.
    "mgsm": buggy_mgsm_extract,
    "mgsm_robust": robust_mgsm_extract,
    "mgsm_buggy_firstnum": buggy_first_number_extract,
    "gpqa": robust_gpqa_extract,
    "game24": robust_game24_extract,
}
