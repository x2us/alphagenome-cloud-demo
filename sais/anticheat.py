"""Anti-cheat SELF-AUDIT gates for SAIS Task 1.

Purpose: let you detect, *before submitting*, the fingerprints that cause the
online grader to zero you for answer-recovery / external reconstruction. This is
a compliance / integrity tool — it helps you stay on the legitimate
clean-pipeline path the analysis already committed to:

    NO-GO: refs-family / skeleton hard-boost families; using suspicious_flag as a
    ranking target; hard saturation beyond the top-1% budget.

These checks flag the patterns; the remedy is to remove the boosting logic, not
to hide the flags. A submission that trips any HARD fingerprint should be treated
as utility 0 locally so the loop never ships it.

The thresholds are conservative defaults; pass your real budget when known.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass


@dataclass
class CheatAudit:
    n_rows: int
    n_targets: int
    near_perfect_rows: int           # score >= near_perfect_threshold
    top1pct_budget: int              # legitimate top-1% slots across targets
    exact_id_matches_to_actives: int # InChIKey-exact matches to known actives
    repeated_score_max_run: int      # largest group of identical scores
    hard_flags: list[str]
    soft_flags: list[str]

    @property
    def passes_hard_gate(self) -> bool:
        return not self.hard_flags

    def explain(self) -> str:
        out = [f"anti-cheat audit: rows={self.n_rows} targets={self.n_targets}",
               f"  near-perfect (>=thr) rows : {self.near_perfect_rows} "
               f"(top-1% budget {self.top1pct_budget})",
               f"  exact-id == known actives : {self.exact_id_matches_to_actives}",
               f"  largest identical-score run: {self.repeated_score_max_run}"]
        for f in self.hard_flags:
            out.append(f"  HARD  {f}")
        for f in self.soft_flags:
            out.append(f"  soft  {f}")
        return "\n".join(out)


def audit(
    scores: list[float],
    target_of_row: list[str],
    known_active_ids: set[str] | None = None,
    row_ids: list[str] | None = None,
    near_perfect_threshold: float = 0.9999,
    saturation_budget_multiple: float = 1.0,
) -> CheatAudit:
    """Audit a submission for answer-recovery / saturation fingerprints.

    * Saturation budget: number of near-perfect rows should not exceed the
      legitimate top-1% slot count (sum over targets of ceil(0.01 * rows_t)).
      Far exceeding it is the "86/102 targets saturated beyond top-1%" pattern.
    * External reconstruction: exact id-matches of high-scoring rows to known
      actives, and long runs of identical scores, are reconstruction fingerprints.
    """
    n = len(scores)
    targets = Counter(target_of_row)
    n_targets = len(targets)

    near_perfect = sum(1 for s in scores if s >= near_perfect_threshold)
    top1_budget = sum(max(1, math.ceil(0.01 * c)) for c in targets.values())

    # Largest run of identical score values (reconstruction often pins exact vals).
    score_counts = Counter(round(s, 6) for s in scores)
    max_run = max(score_counts.values()) if score_counts else 0

    exact_matches = 0
    if known_active_ids and row_ids:
        for rid, s in zip(row_ids, scores):
            if s >= near_perfect_threshold and rid in known_active_ids:
                exact_matches += 1

    hard, soft = [], []
    budget = int(top1_budget * saturation_budget_multiple)
    if near_perfect > budget:
        hard.append(
            f"saturation: {near_perfect} near-perfect rows exceed top-1% budget "
            f"{budget} -> hard-boost/answer-recovery fingerprint")
    if exact_matches > 0:
        hard.append(
            f"external reconstruction: {exact_matches} near-perfect rows id-match "
            f"known actives exactly")
    if max_run > max(10, budget):
        soft.append(f"{max_run} rows share one exact score value (pinning fingerprint)")
    if near_perfect > 0 and near_perfect <= budget:
        soft.append(f"{near_perfect} near-perfect rows within budget (review intent)")

    return CheatAudit(
        n_rows=n, n_targets=n_targets, near_perfect_rows=near_perfect,
        top1pct_budget=top1_budget, exact_id_matches_to_actives=exact_matches,
        repeated_score_max_run=max_run, hard_flags=hard, soft_flags=soft,
    )
