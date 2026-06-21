"""Evaluation harness: run one track end-to-end and return a utility score.

This is the ``interact`` + utility function from the paper: the agent runs its
current policy against the environment (a track) and gets a scalar reward.

CRITICAL SAFEGUARD (the fix for "silent zero"): :func:`run_track` returns a
rich ``Result`` that records *why* items failed — in particular how many items
produced an *unparseable* prediction. A track scoring 0 because the extractor
returned ``None`` for every item is a completely different situation from a
track scoring 0 because the model got every answer wrong, and the harness must
not hide that. ``Result.is_suspicious_zero`` flags the former so the loop can
treat it as a pipeline bug rather than a valid (un-improvable) utility of 0.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import extract as extract_mod
from .llm import LLMBackend, get_backend
from .tracks import TRACKS


@dataclass
class Result:
    track: str
    extractor: str
    n: int
    correct: int
    none_preds: int  # items where extraction returned None (unparseable)
    details: list[dict] = field(default_factory=list)

    @property
    def accuracy(self) -> float:
        return self.correct / self.n if self.n else 0.0

    @property
    def is_suspicious_zero(self) -> bool:
        """A zero that is almost certainly a parsing/pipeline bug, not skill.

        Heuristic: score is 0 AND a large majority of predictions were
        unparseable. With a real model that should essentially never happen
        unless the extractor is incompatible with the output format.
        """
        return self.correct == 0 and self.n > 0 and self.none_preds >= max(1, int(0.8 * self.n))

    def __str__(self) -> str:
        flag = "  <-- SUSPICIOUS ZERO (parsing bug, not skill)" if self.is_suspicious_zero else ""
        return (
            f"{self.track:14s} extractor={self.extractor:18s} "
            f"acc={self.accuracy:5.1%} ({self.correct}/{self.n})  "
            f"unparseable={self.none_preds}/{self.n}{flag}"
        )


def run_track(
    track_key: str,
    extractor_key: str | None = None,
    backend: LLMBackend | None = None,
    limit: int | None = None,
) -> Result:
    track = TRACKS[track_key]
    backend = backend or get_backend()
    extractor_key = extractor_key or track.EXTRACTOR
    extractor = extract_mod.EXTRACTORS[extractor_key]

    items = track.load()
    if limit:
        items = items[:limit]

    correct = 0
    none_preds = 0
    details = []
    for item in items:
        prompt = track.build_prompt(item)
        raw = backend.complete(prompt)
        pred = extractor(raw)
        if pred is None:
            none_preds += 1
        # game24 scorer needs the item for number-set validation.
        if track_key == "track3_game24":
            ok = track.score(pred, item["gold"], item)
        else:
            ok = track.score(pred, item["gold"])
        correct += int(ok)
        details.append({"gold": item["gold"], "pred": pred, "ok": ok, "raw": raw})

    return Result(
        track=track_key,
        extractor=extractor_key,
        n=len(items),
        correct=correct,
        none_preds=none_preds,
        details=details,
    )
