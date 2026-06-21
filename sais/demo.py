#!/usr/bin/env python3
"""Worked example of the verifier-first utility on two synthetic candidates:

  A) a "hard-boost / answer-recovery" candidate that looks great locally by
     naive accuracy but trips the anti-cheat hard gate AND mislogs its config
     -> GATED ZERO (this is what scores 0 online).
  B) a clean candidate (no refs/no saturation, truthful log) with a modest but
     REAL local Mean EF1% improvement -> non-zero utility.

Run:  python -m sais.demo

The numbers are synthetic fixtures; the point is the control flow, which is
identical against your real artifact once you wire the gate callables to it.
"""

from __future__ import annotations

import random

from .anticheat import audit
from .ef1 import TargetScores, mean_ef1
from .log_truth import check as log_check
from .utility import GateResult, evaluate


def _entry_contract_gate(ok: bool, detail: str):
    return lambda: GateResult("entry_contract", ok, detail)


def _output_artifact_gate(rows: int, expected: int):
    return lambda: GateResult("output_artifact", rows == expected,
                              f"{rows} rows (expected {expected})")


def _anticheat_gate(scores, targets, known_actives, row_ids):
    def g():
        a = audit(scores, targets, known_actives, row_ids)
        return GateResult("anticheat_hard_gate", a.passes_hard_gate,
                          "; ".join(a.hard_flags) or "clean")
    return g


def _logtruth_gate(log_text, executed):
    def g():
        r = log_check(log_text, executed)
        return GateResult("log_truthfulness", r.passed, "; ".join(r.mismatches) or "consistent")
    return g


def _ef1_proxy_gate(targets, baseline_mean):
    def g():
        res = mean_ef1(targets)
        improvement = res["mean_ef"] - baseline_mean
        # Proxy score: clip improvement into (0, 1]; <=0 means no real gain.
        score = max(0.0, min(1.0, 0.5 + improvement / 20.0)) if improvement > 0 else 0.0
        return GateResult("local_ef1_proxy", improvement > 0,
                          f"mean_EF1%={res['mean_ef']:.2f} (baseline {baseline_mean:.2f}, "
                          f"delta {improvement:+.2f})", score=score)
    return g


def _make_targets(rng, boost_actives: bool) -> list[TargetScores]:
    targets = []
    for t in range(5):
        labels, scores, ids = [], [], []
        for i in range(200):
            active = i < 10  # 10 actives, 190 decoys
            labels.append(int(active))
            ids.append(f"T{t}_C{i}")
            if active and boost_actives:
                scores.append(0.99995)            # answer-recovery: pin actives near 1
            elif active:
                scores.append(rng.uniform(0.55, 0.8))   # legit: actives somewhat enriched
            else:
                scores.append(rng.uniform(0.0, 0.6))
        targets.append(TargetScores(f"T{t}", labels, scores, ids))
    return targets


def main() -> None:
    rng = random.Random(0)

    print("### Candidate A: hard-boost / answer-recovery (mislogged) ###")
    ta = _make_targets(rng, boost_actives=True)
    scores_a = [s for t in ta for s in t.scores]
    tgt_a = [t.target for t in ta for _ in t.scores]
    ids_a = [i for t in ta for i in t.ids]
    known_actives = {i for t in ta for i, lab in zip(t.ids, t.labels) if lab == 1}
    log_a = "Metric: Mean EF1%\ninchikey_boost=False\nexact_tiebreak=False\n"
    executed_a = {"metric": "MannWhitneyAUC", "inchikey_boost": True, "exact_tiebreak": True}
    report_a = evaluate(
        hard_gates=[
            _entry_contract_gate(True, "entrypoint + /saisdata mount ok"),
            _output_artifact_gate(1000, 1000),
            _anticheat_gate(scores_a, tgt_a, known_actives, ids_a),
            _logtruth_gate(log_a, executed_a),
        ],
        proxy_gates=[_ef1_proxy_gate(ta, baseline_mean=8.0)],
    )
    print(report_a.explain(), "\n")

    print("### Candidate B: clean, truthful, modest real gain ###")
    tb = _make_targets(rng, boost_actives=False)
    scores_b = [s for t in tb for s in t.scores]
    tgt_b = [t.target for t in tb for _ in t.scores]
    ids_b = [i for t in tb for i in t.ids]
    log_b = "Metric: Mean EF1%\ninchikey_boost=False\nexact_tiebreak=False\n"
    executed_b = {"metric": "Mean EF1%", "inchikey_boost": False, "exact_tiebreak": False}
    report_b = evaluate(
        hard_gates=[
            _entry_contract_gate(True, "entrypoint + /saisdata mount ok"),
            _output_artifact_gate(1000, 1000),
            _anticheat_gate(scores_b, tgt_b, known_actives, ids_b),
            _logtruth_gate(log_b, executed_b),
        ],
        proxy_gates=[_ef1_proxy_gate(tb, baseline_mean=8.0)],
    )
    print(report_b.explain())


if __name__ == "__main__":
    main()
