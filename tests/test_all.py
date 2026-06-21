"""Tests for the Gödel toy reproduction and the SAIS verifier-first utility."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["GODEL_BACKEND"] = "stub"

from godel_agent.agent import GodelAgent          # noqa: E402
from godel_agent.harness import run_track          # noqa: E402
from sais.anticheat import audit                    # noqa: E402
from sais.ef1 import TargetScores, mean_ef1, enrichment_factor, ReferenceLeakageError  # noqa: E402
from sais.log_truth import check as log_check       # noqa: E402
from sais.utility import GateResult, evaluate       # noqa: E402


# ---- Gödel toy reproduction ------------------------------------------------ #

def test_track1_buggy_is_suspicious_zero():
    r = run_track("track1_mgsm")               # buggy extractor (as shipped)
    assert r.accuracy == 0.0
    assert r.is_suspicious_zero               # flagged as parsing bug, not skill

def test_track1_robust_recovers():
    r = run_track("track1_mgsm", "mgsm_robust")
    assert r.accuracy == 1.0
    assert not r.is_suspicious_zero

def test_other_tracks_not_zero():
    assert run_track("track2_gpqa").accuracy > 0
    assert run_track("track3_game24").accuracy > 0

def test_agent_self_repairs_verifier_first():
    agent = GodelAgent(track_key="track1_mgsm")
    final = agent.continue_improve()
    assert final.accuracy == 1.0
    actions = [s.action for s in agent.history]
    assert "self_update" in actions           # it actually changed the meta-rule


# ---- SAIS verifier-first utility ------------------------------------------- #

def test_enrichment_factor_basic():
    # 100 compounds, 10 actives all ranked top -> EF1% (k=1) is max for that slot.
    labels = [1] * 10 + [0] * 90
    scores = list(range(100, 0, -1))
    ef = enrichment_factor(labels, scores, 0.01)
    assert ef > 1.0

def test_reference_leakage_raises():
    ts = TargetScores("T", labels=[1, 0], scores=[0.9, 0.1], ids=["A", "B"],
                      reference_ids=frozenset({"A"}))
    try:
        mean_ef1([ts])
        assert False, "expected ReferenceLeakageError"
    except ReferenceLeakageError:
        pass

def test_anticheat_flags_saturation_and_reconstruction():
    scores = [0.99995] * 50 + [0.3] * 150
    targets = [f"T{i//40}" for i in range(200)]
    ids = [f"id{i}" for i in range(200)]
    known = {f"id{i}" for i in range(50)}
    a = audit(scores, targets, known, ids)
    assert not a.passes_hard_gate
    assert a.exact_id_matches_to_actives == 50

def test_anticheat_clean_passes():
    scores = [0.2 + 0.001 * i for i in range(200)]
    targets = [f"T{i//40}" for i in range(200)]
    a = audit(scores, targets, set(), [f"id{i}" for i in range(200)])
    assert a.passes_hard_gate

def test_log_truthfulness_detects_mismatch():
    r = log_check("Metric: Mean EF1%\ninchikey_boost=False\n",
                  {"metric": "MannWhitneyAUC", "inchikey_boost": True})
    assert not r.passed
    assert len(r.mismatches) == 2

def test_utility_is_fail_closed_and_gated_zero():
    report = evaluate(
        hard_gates=[
            lambda: GateResult("entry", True),
            lambda: GateResult("anticheat", False, "external reconstruction"),
        ],
        proxy_gates=[lambda: GateResult("ef1", True, score=1.0)],
    )
    assert report.utility == 0.0
    assert report.is_gated_zero
    assert report.first_failure.name == "anticheat"

def test_utility_clean_is_nonzero():
    report = evaluate(
        hard_gates=[lambda: GateResult("entry", True), lambda: GateResult("anticheat", True)],
        proxy_gates=[lambda: GateResult("ef1", True, score=0.7)],
    )
    assert abs(report.utility - 0.7) < 1e-9
    assert not report.is_gated_zero


if __name__ == "__main__":
    import traceback
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        try:
            fn()
            print(f"PASS {fn.__name__}")
            passed += 1
        except Exception:
            print(f"FAIL {fn.__name__}")
            traceback.print_exc()
    print(f"\n{passed}/{len(fns)} passed")
    sys.exit(0 if passed == len(fns) else 1)
