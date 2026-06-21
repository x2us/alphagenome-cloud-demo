"""SAIS verifier-first utility harness.

Repairs the "Task 1 always scores 0" failure by making the *local* utility a
faithful, fail-closed surrogate of the online grader:

    U = entry_contract * output_artifact * anticheat_hard_gate
        * log_truthfulness * local_EF1%_proxy

See ``utility.evaluate`` to compose gates and ``demo.py`` for a worked example.
"""

from . import anticheat, contract, ef1, log_truth, pipeline, release_card, submission, utility

__all__ = ["utility", "ef1", "anticheat", "log_truth",
           "submission", "contract", "release_card", "pipeline"]
