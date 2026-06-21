"""Verifier-first utility for SAIS Task 1 — the corrected ``U``.

The root cause of "Task 1 always scores 0" is NOT a missing clever algorithm.
It is that the recursive-improvement loop optimised the wrong utility. The loop
kept editing the *candidate* (the screening model) while never proving that the
*candidate's entry contract, anti-cheat posture, log truthfulness, and local
EF1% proxy* were trustworthy.

In Gödel-Agent terms (arXiv:2410.04444): every self-modification must be judged
by an environment utility function. If that utility is "online score went up",
and the online grader returns 0 whenever any upstream hard gate fails, then the
fitness landscape is flat at 0 — the loop gets no gradient and can never climb
out, no matter how good the model is. The fix is to make the *local* utility a
faithful, multiplicative surrogate of how the online grader actually behaves:

    U = entry_contract            (0/1)
      * output_artifact           (0/1)
      * anticheat_hard_gate       (0/1)   <-- external-reconstruction etc. ZERO you
      * log_truthfulness          (0/1)
      * local_official_proxy      (continuous, e.g. Mean EF1% improvement)

If any of the first four binary gates is 0, U is 0 — and crucially we record
*which* gate failed, so a zero is never mistaken for "weak model". This is the
same gated-zero vs skill-zero distinction the toy reproduction makes, applied to
the real competition.

This module is data-/schema-agnostic: you supply gate callables that inspect
your real artifact (result.log, the submission file, /saisdata mount). It runs
against fixtures here and against your real workspace unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


@dataclass
class GateResult:
    name: str
    passed: bool
    detail: str = ""
    # For the continuous proxy gate only:
    score: float | None = None


@dataclass
class UtilityReport:
    gates: list[GateResult] = field(default_factory=list)

    @property
    def hard_gates(self) -> list[GateResult]:
        return [g for g in self.gates if g.score is None]

    @property
    def proxy_gates(self) -> list[GateResult]:
        return [g for g in self.gates if g.score is not None]

    @property
    def first_failure(self) -> GateResult | None:
        for g in self.hard_gates:
            if not g.passed:
                return g
        return None

    @property
    def utility(self) -> float:
        """Multiplicative, fail-closed utility."""
        for g in self.hard_gates:
            if not g.passed:
                return 0.0
        # All hard gates pass -> utility is the product of proxy scores (>=0).
        u = 1.0
        for g in self.proxy_gates:
            u *= max(0.0, g.score if g.score is not None else 0.0)
        return u

    @property
    def is_gated_zero(self) -> bool:
        """Zero caused by a hard-gate failure (pipeline/anti-cheat), not skill."""
        return self.utility == 0.0 and self.first_failure is not None

    def explain(self) -> str:
        lines = ["Verifier-first utility report", "=" * 40]
        for g in self.gates:
            status = "PASS" if g.passed else "FAIL"
            extra = f" score={g.score:.4f}" if g.score is not None else ""
            lines.append(f"  [{status}] {g.name}{extra}  {g.detail}")
        lines.append("-" * 40)
        if self.is_gated_zero:
            lines.append(f"GATED ZERO -> blocked by: {self.first_failure.name}  "
                         f"({self.first_failure.detail})")
            lines.append("Do NOT tune the model. Repair this gate first.")
        else:
            lines.append(f"U = {self.utility:.4f}")
        return "\n".join(lines)


# A gate is a callable returning a GateResult. ``order`` matters: cheapest /
# most-blocking first so the report names the *first* real blocker.
Gate = Callable[[], GateResult]


def evaluate(hard_gates: list[Gate], proxy_gates: list[Gate]) -> UtilityReport:
    """Run hard gates first (short-circuit semantics are encoded in UtilityReport),
    then proxy gates. All are evaluated so the report is complete, but utility is
    fail-closed on any hard-gate failure.
    """
    report = UtilityReport()
    for g in hard_gates:
        report.gates.append(g())
    # Only meaningful if hard gates pass, but we still compute for visibility.
    for g in proxy_gates:
        report.gates.append(g())
    return report
