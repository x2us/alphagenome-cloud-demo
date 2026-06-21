"""Gödel Agent — a compact, runnable implementation of the recursive
self-improvement loop from arXiv:2410.04444, plus a verifier-first utility
harness (see ``sais/``) that fixes the "a whole track always scores 0" failure.
"""

from .agent import GodelAgent
from .harness import run_track, Result

__all__ = ["GodelAgent", "run_track", "Result"]
