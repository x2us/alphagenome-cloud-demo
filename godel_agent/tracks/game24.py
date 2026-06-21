"""Track 3 — Game of 24.

Given four numbers, find an arithmetic expression using each exactly once that
evaluates to 24. Scoring validates the expression (uses the right numbers AND
equals 24), the same emergent-search task the paper highlights.
"""

from __future__ import annotations

import ast
import re
from collections import Counter

NAME = "track3_game24"
EXTRACTOR = "game24"

_ITEMS = [
    {"numbers": [4, 7, 8, 8], "gold": "(7-8/8)*4"},
    {"numbers": [3, 3, 8, 8], "gold": "8/(3-8/3)"},
    {"numbers": [2, 3, 4, 6], "gold": "(2+4)*(6-3)+6"},  # gold is illustrative; scorer is the source of truth
    {"numbers": [1, 3, 4, 6], "gold": "6/(1-3/4)"},
    {"numbers": [2, 2, 6, 6], "gold": "(2+2)*6"},
    {"numbers": [5, 5, 5, 1], "gold": "(5-1/5)*5"},
]


def load() -> list[dict]:
    return [dict(it) for it in _ITEMS]


def build_prompt(item: dict) -> str:
    nums = ", ".join(str(n) for n in item["numbers"])
    return (
        "[[track:game24]]\n"
        "Game of 24: using each of the numbers exactly once and the operators "
        "+ - * / and parentheses, build an expression that equals 24.\n\n"
        f"Numbers: {nums}\n"
        f"[[gold:{item['gold']}]]"
    )


def _uses_exact_numbers(expr: str, numbers: list[int]) -> bool:
    found = [int(n) for n in re.findall(r"\d+", expr)]
    return Counter(found) == Counter(numbers)


def _safe_eval(expr: str) -> float | None:
    try:
        node = ast.parse(expr, mode="eval")
    except SyntaxError:
        return None
    allowed = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Num, ast.Constant,
               ast.Add, ast.Sub, ast.Mult, ast.Div, ast.USub, ast.UAdd)
    for n in ast.walk(node):
        if not isinstance(n, allowed):
            return None
    try:
        return eval(compile(node, "<expr>", "eval"), {"__builtins__": {}}, {})
    except ZeroDivisionError:
        return None


def score(pred: str | None, gold: str, item: dict | None = None) -> bool:
    """Validate the predicted expression. ``gold`` is unused for validation —
    correctness is defined by the rules, not by matching a single solution."""
    if pred is None:
        return False
    numbers = item["numbers"] if item else [int(n) for n in re.findall(r"\d+", gold)]
    if not _uses_exact_numbers(pred, numbers):
        return False
    val = _safe_eval(pred)
    return val is not None and abs(val - 24) < 1e-6
