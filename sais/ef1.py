"""Honest local Mean EF1% proxy for SAIS Task 1.

EF1% (enrichment factor at the top 1%) is the standard virtual-screening metric:

    EF_{x%} = (actives_in_top_x% / N_in_top_x%) / (total_actives / N_total)

Mean EF1% averages EF_{1%} across targets. The online grader uses (a variant of)
this; the local proxy must match it so the recursive loop has a *truthful*
gradient rather than the Mann-Whitney `_auc` surrogate the shipped code actually
optimised while the log claimed "Mean EF1%".

Two anti-self-deception rules are enforced, because a proxy that lets you peek at
the answer is worse than no proxy (it makes a cheating pipeline look great
locally and then score 0 online):

  1. HELD-OUT REFERENCES. If your score is similarity-to-reference-actives,
     references must be a disjoint split from the scored set.
  2. NO SAME-TARGET LEAKAGE. A target's own DUD-E actives must never enter its
     reference set. ``mean_ef1`` refuses to score if leakage is detected.

This module computes EF from (label, score) lists you produce with your real
model on PUBLIC DUD-E actives/decoys. It does not download anything and does not
embed answers; the fixtures are synthetic.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class TargetScores:
    target: str
    # Parallel lists: label 1 = active, 0 = decoy; score = your model's score.
    labels: list[int]
    scores: list[float]
    # InChIKeys (or any id) used to detect same-target reference leakage.
    ids: list[str] | None = None
    reference_ids: frozenset[str] = frozenset()


def enrichment_factor(labels: list[int], scores: list[float], fraction: float = 0.01) -> float:
    n = len(labels)
    if n == 0:
        return 0.0
    total_actives = sum(labels)
    if total_actives == 0:
        return 0.0
    k = max(1, math.floor(n * fraction))
    # Rank by descending score; stable so ties don't favour actives.
    order = sorted(range(n), key=lambda i: scores[i], reverse=True)
    top = order[:k]
    actives_in_top = sum(labels[i] for i in top)
    return (actives_in_top / k) / (total_actives / n)


class ReferenceLeakageError(ValueError):
    """A target's own active appears in its reference set -> self-deception."""


def _check_leakage(ts: TargetScores) -> None:
    if not ts.reference_ids or ts.ids is None:
        return
    own_actives = {i for i, lab in zip(ts.ids, ts.labels) if lab == 1}
    leaked = own_actives & set(ts.reference_ids)
    if leaked:
        raise ReferenceLeakageError(
            f"target {ts.target}: {len(leaked)} same-target active(s) used as references "
            f"-> EF1% would be self-deceptively high; exclude them."
        )


def mean_ef1(targets: list[TargetScores], fraction: float = 0.01,
             strict: bool = True) -> dict:
    """Return Mean EF{fraction}% and per-target EFs.

    With ``strict=True`` (default) any same-target reference leakage raises,
    forcing an honest proxy. The returned dict is suitable as a proxy gate score
    (use the *improvement* over a baseline as the utility, per the paper).
    """
    per_target = {}
    for ts in targets:
        if strict:
            _check_leakage(ts)
        per_target[ts.target] = enrichment_factor(ts.labels, ts.scores, fraction)
    mean = sum(per_target.values()) / len(per_target) if per_target else 0.0
    return {"mean_ef": mean, "fraction": fraction, "per_target": per_target,
            "n_targets": len(per_target)}
