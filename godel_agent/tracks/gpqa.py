"""Track 2 — GPQA-style graduate science multiple choice (answer = A-D)."""

from __future__ import annotations

NAME = "track2_gpqa"
EXTRACTOR = "gpqa"

_ITEMS = [
    {"question": "Which particle mediates the electromagnetic force?\n(A) Gluon (B) Photon (C) W boson (D) Graviton", "gold": "B"},
    {"question": "In an SN2 reaction, the rate depends on:\n(A) Substrate only (B) Nucleophile only (C) Both substrate and nucleophile (D) Neither", "gold": "C"},
    {"question": "The Chandrasekhar limit is approximately:\n(A) 0.5 solar masses (B) 1.4 solar masses (C) 3.0 solar masses (D) 8.0 solar masses", "gold": "B"},
    {"question": "Which enzyme unwinds DNA at the replication fork?\n(A) Ligase (B) Primase (C) Helicase (D) Polymerase", "gold": "C"},
    {"question": "The Carnot efficiency depends only on:\n(A) Working fluid (B) Hot and cold reservoir temperatures (C) Engine size (D) Pressure", "gold": "B"},
    {"question": "Hardy-Weinberg equilibrium assumes:\n(A) Mutation (B) Selection (C) No migration, mutation, or selection (D) Genetic drift", "gold": "C"},
]


def load() -> list[dict]:
    return [dict(it) for it in _ITEMS]


def build_prompt(item: dict) -> str:
    return (
        "[[track:gpqa]]\n"
        "Answer the multiple-choice question. Give brief reasoning, then state "
        "the answer as a single letter.\n\n"
        f"{item['question']}\n"
        f"[[gold:{item['gold']}]]"
    )


def score(pred: str | None, gold: str) -> bool:
    return pred is not None and pred.strip().upper() == gold.strip().upper()
