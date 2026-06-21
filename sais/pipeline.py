"""G0–G3 候选队列状态机 —— 把"先改 U → 再改 I → 最后改 π"的工作流编码。

  G0 冻结真相源：只有带 release card + pull-back 的候选算真相，其余降级历史。
  G1 元验证器优先：候选必须过全部硬门（入口/产物/合规/mount-truth/release card）
                   并给出本机代理分（不是线上分）。
  G2 单因子递归改进：每轮只允许一个主要改动；失败回滚到父代，不混合修复。
  G3 提交前 Gödel 审查：所有门 + release card 齐全，且单因子可定因，才进提交队列。

设计要点：本状态机**不替你跑模型**，它裁决"一个候选是否值得进入提交队列"。
把真实门结果（GateResult）+ release card 喂进来，它给出 ADMIT / REJECT / ROLLBACK。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .release_card import ReleaseCard, check_release_card
from .utility import GateResult, UtilityReport


class Decision(Enum):
    ADMIT = "ADMIT"        # 进入提交队列
    REJECT = "REJECT"      # 不合规/未过门，丢弃
    ROLLBACK = "ROLLBACK"  # 比父代差，回滚到父代


@dataclass
class Candidate:
    cid: str
    task: str                       # task1 / task2 / task3
    parent_cid: str | None
    single_factor: str              # 相对父代的唯一改动（G2）
    hard_gates: list[GateResult]    # 入口/产物/合规/mount-truth 等
    proxy_score: float | None       # 本机代理分（越高越好；None=未评）
    release_card: ReleaseCard


@dataclass
class Verdict:
    cid: str
    decision: Decision
    reasons: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        return f"[{self.decision.value}] {self.cid}: " + "；".join(self.reasons)


@dataclass
class Pipeline:
    # 记录每个 task 当前已进入提交队列的最优候选（含其代理分）。
    best: dict[str, Candidate] = field(default_factory=dict)
    queue: list[Candidate] = field(default_factory=list)
    log: list[Verdict] = field(default_factory=list)

    def review(self, c: Candidate) -> Verdict:
        reasons: list[str] = []

        # G2：单因子约束。
        if not c.single_factor:
            return self._record(Verdict(c.cid, Decision.REJECT,
                                        ["未声明单因子改动（G2），无法定因"]))
        if any(sep in c.single_factor for sep in (",", "，", "+", "；", ";", " and ", " 和 ")):
            return self._record(Verdict(c.cid, Decision.REJECT,
                ["多因子混合改动（G2 违规），无法定因 —— 拆成单因子逐个提交"]))

        # G1：硬门必须全绿。
        failed = [g.name for g in c.hard_gates if not g.passed]
        if failed:
            return self._record(Verdict(c.cid, Decision.REJECT,
                                        [f"硬门未过: {failed}"]))

        # G1/G0：release card 门。
        rc = check_release_card(c.release_card)
        if not rc.passed:
            return self._record(Verdict(c.cid, Decision.REJECT,
                                        [f"release card 不齐: {rc.detail}"]))

        # G2：与父代比较代理分；更差则回滚。
        parent = self.best.get(c.task)
        if parent is not None and c.proxy_score is not None and parent.proxy_score is not None:
            if c.proxy_score <= parent.proxy_score:
                return self._record(Verdict(c.cid, Decision.ROLLBACK,
                    [f"代理分 {c.proxy_score:.4f} 未超父代 {parent.proxy_score:.4f}，回滚"]))

        # G3：通过，进入提交队列并成为该 task 当前最优。
        reasons.append(f"全门绿 + release card 齐全 + 单因子'{c.single_factor}'")
        self.queue.append(c)
        self.best[c.task] = c
        return self._record(Verdict(c.cid, Decision.ADMIT, reasons))

    def submittable(self, task: str) -> Candidate | None:
        """该 task 当前唯一可提交候选（裸地址从 release_card.image_reference 取）。"""
        return self.best.get(task)

    def _record(self, v: Verdict) -> Verdict:
        self.log.append(v)
        return v
