"""Release card —— G1 的"release card 门"与 G3 提交前 Gödel 审查的证据链。

铁律：没有 release card 的地址一律降级为历史信息，不得进入提交队列（G0）。
一张合格的 release card 必须能回答：这是什么 digest、能否 pull-back、smoke 是否
绿、日志摘要是什么、相对父代只改了哪一个因子（G2 单因子）。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .utility import GateResult


@dataclass
class ReleaseCard:
    image_digest: str = ""            # sha256:...，pull-back 实测得到
    image_reference: str = ""         # 裸地址
    pullback_verified: bool = False   # 是否回拉实测过
    smoke_passed: bool = False        # 空挂载 smoke 是否绿（产物非空、fail-closed）
    log_summary: str = ""             # 关键日志摘要
    single_factor: str = ""           # 相对父代唯一改动（G2）
    parent_digest: str = ""           # 父代 digest，便于回滚
    gate_report: str = ""             # G1 门汇总
    notes: str = ""

    def missing_fields(self) -> list[str]:
        miss = []
        if not self.image_digest.startswith("sha256:"):
            miss.append("image_digest（需 pull-back 实测的 sha256）")
        if not self.image_reference:
            miss.append("image_reference（裸地址）")
        if not self.pullback_verified:
            miss.append("pullback_verified")
        if not self.smoke_passed:
            miss.append("smoke_passed")
        if not self.log_summary:
            miss.append("log_summary")
        if not self.single_factor:
            miss.append("single_factor（G2 单因子改动说明）")
        return miss


def check_release_card(card: ReleaseCard) -> GateResult:
    miss = card.missing_fields()
    detail = "release card 齐全" if not miss else f"缺字段: {miss}"
    return GateResult("release_card", not miss, detail)
