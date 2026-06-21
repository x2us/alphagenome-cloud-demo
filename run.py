#!/usr/bin/env python3
"""Minimal reproduction: a track that "always scores 0", and the Gödel Agent
repairing it by fixing the utility/extractor instead of the model.

    python run.py            # run all three tracks, show the zero + the fix
    python run.py --agent    # let the Gödel Agent self-repair Track 1

This is the toy analogue of the SAIS Task-1 situation: utility gated to 0 by an
upstream parsing/contract bug yields a flat landscape no amount of "smarter
model" can climb. Fix the verifier first; the score follows.
"""

import argparse

from godel_agent.agent import GodelAgent
from godel_agent.harness import run_track
from godel_agent.tracks import TRACKS


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", action="store_true", help="run the self-improvement loop on Track 1")
    args = ap.parse_args()

    if args.agent:
        agent = GodelAgent(track_key="track1_mgsm")
        final = agent.continue_improve()
        print("Gödel Agent self-improvement trace (Track 1):")
        for s in agent.history:
            print(f"  iter {s.iteration}: {s.action:11s} {s.extractor_key:14s} "
                  f"acc={s.accuracy:5.1%} suspicious_zero={s.suspicious_zero}  {s.note}")
        print(f"\nFinal: extractor={final.extractor} acc={final.accuracy:.1%}")
        return

    print("=== As-shipped (Track 1 uses the buggy extractor) ===")
    for key in TRACKS:
        print("  " + str(run_track(key)))

    print("\n=== Track 1 with the robust extractor (the fix) ===")
    print("  " + str(run_track("track1_mgsm", "mgsm_robust")))


if __name__ == "__main__":
    main()
