"""A compact, paper-faithful Gödel Agent loop.

Implements the four operations from arXiv:2410.04444:

    self_inspect   -> read own policy + meta-policy (here: the active extractor)
    interact       -> run the policy against the environment, get utility r
    self_update    -> generate/apply a modification (swap extractor / prompt)
    continue_improve -> recurse if a better candidate exists

The two ablation-critical features the paper highlights are built in:
    * Reflection    : decide WHAT to change from the failure signature.
    * Error handling : every self_update is trial-applied and ROLLED BACK if it
                       throws or fails to improve utility — bad modifications are
                       common and must not corrupt the running agent.

The crucial design point for the "Task always scores 0" problem: the agent
only ever trusts utility from a verifier that can tell a *gated zero* (broken
pipeline) from a *skill zero*. A flat, all-zero landscape yields no gradient, so
the loop first repairs the verifier/contract, THEN optimises the policy. This is
exactly the verifier-before-candidate ordering the SAIS analysis arrives at.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .harness import Result, run_track
from .llm import LLMBackend, get_backend


@dataclass
class Candidate:
    extractor_key: str
    rationale: str


@dataclass
class Step:
    iteration: int
    action: str
    extractor_key: str
    accuracy: float
    suspicious_zero: bool
    note: str


@dataclass
class GodelAgent:
    track_key: str
    backend: LLMBackend = field(default_factory=get_backend)
    active_extractor: str | None = None  # the policy's meta-rule (parser)
    history: list[Step] = field(default_factory=list)

    # ---- the four operations -------------------------------------------- #

    def self_inspect(self) -> str:
        """Return the current policy/meta-policy under modification."""
        from .tracks import TRACKS
        if self.active_extractor is None:
            self.active_extractor = TRACKS[self.track_key].EXTRACTOR
        return self.active_extractor

    def interact(self, extractor_key: str | None = None) -> Result:
        return run_track(self.track_key, extractor_key or self.active_extractor, self.backend)

    def reflect(self, result: Result) -> Candidate | None:
        """Decide the next modification from the failure signature.

        This is the meta-rule. A *suspicious zero* (everything unparseable) is
        diagnosed as a parser/contract bug, NOT weak reasoning, so the fix is to
        replace the extractor — the change that actually moves utility.
        """
        if result.is_suspicious_zero:
            # Reflection: the model produced answers but extraction failed.
            return Candidate(
                extractor_key=self._robust_variant(result.extractor),
                rationale=(
                    "All predictions unparseable -> output-format/extractor mismatch, "
                    "not a reasoning failure. Swap to the robust extractor."
                ),
            )
        return None  # already healthy; nothing obvious to improve

    def self_update(self, candidate: Candidate) -> Result | None:
        """Trial-apply a candidate with error handling + rollback.

        Returns the candidate's result if it strictly improves utility, else
        None (and the agent state is left untouched).
        """
        previous = self.active_extractor
        try:
            trial = self.interact(candidate.extractor_key)
        except Exception:
            return None  # error handling: a throwing modification is discarded
        baseline = self.interact(previous)
        if trial.accuracy > baseline.accuracy:
            self.active_extractor = candidate.extractor_key  # commit
            return trial
        return None  # rollback: no improvement

    # ---- driver --------------------------------------------------------- #

    def continue_improve(self, max_iters: int = 5) -> Result:
        self.self_inspect()
        result = self.interact()
        self._log(0, "interact", result, "initial policy")
        for i in range(1, max_iters + 1):
            candidate = self.reflect(result)
            if candidate is None:
                self._log(i, "stop", result, "no improving candidate found")
                break
            improved = self.self_update(candidate)
            if improved is None:
                self._log(i, "rollback", result, "candidate did not improve utility")
                break
            result = improved
            self._log(i, "self_update", result, candidate.rationale)
        return result

    # ---- helpers -------------------------------------------------------- #

    @staticmethod
    def _robust_variant(extractor_key: str) -> str:
        mapping = {"mgsm": "mgsm_robust", "mgsm_buggy_firstnum": "mgsm_robust"}
        return mapping.get(extractor_key, extractor_key)

    def _log(self, i: int, action: str, result: Result, note: str) -> None:
        self.history.append(
            Step(i, action, result.extractor, result.accuracy, result.is_suspicious_zero, note)
        )
