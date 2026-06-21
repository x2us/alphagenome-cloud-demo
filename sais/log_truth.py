"""Log-truthfulness gate for SAIS Task 1.

The shipped artifact's ``result.log`` claimed ``Metric: Mean EF1%`` while the
code actually selected ``alpha`` with a Mann-Whitney ``_auc`` surrogate, and the
log claimed ``inchikey_boost=False`` while the artifact ran with it True. A
self-improving loop that trusts its own log is optimising a lie.

This gate compares CLAIMED configuration (parsed from result.log) against
EXECUTED configuration (a dict you obtain by actually running / instrumenting the
candidate, not by reading the source). Any mismatch fails the gate -> utility 0,
because you cannot trust a candidate whose log misreports what it did.

Mapping to the analysis' step 1 ("配置实测门") and step 2 ("修日志真实性").
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


# Keys we insist the log states truthfully. Extend as needed.
_BOOL_KEYS = ("inchikey_boost", "exact_tiebreak")
_METRIC_RE = re.compile(r"Metric\s*[:=]\s*([A-Za-z0-9 %._-]+)", re.IGNORECASE)


def parse_log_claims(log_text: str) -> dict:
    claims: dict = {}
    m = _METRIC_RE.search(log_text)
    if m:
        claims["metric"] = m.group(1).strip()
    for key in _BOOL_KEYS:
        km = re.search(rf"{key}\s*[:=]\s*(true|false)", log_text, re.IGNORECASE)
        if km:
            claims[key] = km.group(1).lower() == "true"
    return claims


@dataclass
class LogTruthResult:
    passed: bool
    mismatches: list[str] = field(default_factory=list)
    claims: dict = field(default_factory=dict)
    executed: dict = field(default_factory=dict)

    def explain(self) -> str:
        head = "log truthfulness: " + ("PASS" if self.passed else "FAIL")
        return "\n".join([head] + [f"  mismatch: {m}" for m in self.mismatches])


def check(log_text: str, executed_config: dict) -> LogTruthResult:
    """``executed_config`` MUST come from real execution/instrumentation of the
    candidate (e.g. values written by the run itself), never from reading source.
    """
    claims = parse_log_claims(log_text)
    mismatches: list[str] = []

    # Metric truthfulness: claimed optimisation target must equal executed one.
    if "metric" in claims and "metric" in executed_config:
        if _norm(claims["metric"]) != _norm(executed_config["metric"]):
            mismatches.append(
                f"metric: log claims '{claims['metric']}' but executed "
                f"'{executed_config['metric']}'")
    elif "metric" in claims and "metric" not in executed_config:
        mismatches.append(f"metric: log claims '{claims['metric']}' but execution "
                          f"did not report a metric (cannot verify)")

    for key in _BOOL_KEYS:
        if key in claims and key in executed_config and claims[key] != executed_config[key]:
            mismatches.append(
                f"{key}: log claims {claims[key]} but executed {executed_config[key]}")

    return LogTruthResult(passed=not mismatches, mismatches=mismatches,
                          claims=claims, executed=executed_config)


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(s).lower())
