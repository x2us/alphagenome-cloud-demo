"""G1 元验证器的硬门：入口契约 / 产物完整 / mount-truth(fail-closed)。

本轮已定死的 Task1 真因（交叉验证确认）：
  线上 `/saisdata` 是空目录，旧 `run.sh` fallback 到 `/app/benchmark.zip`，
  随后跑了 117 tasks / 2,092,260 行 —— 它确实跑完了，但跑的是**烤入样本**，
  不是真实挂载数据，所以 0 分合理。

教训：空挂载时**绝不能** fallback 到烤入 zip 偷偷跑完，必须 **fail-closed**
（检测到空挂载即非零退出 / 等待挂载就绪），否则会"成功地"产出一个 0 分产物。
`check_mount_truth` 与 `check_run_sh` 把这条变成可执行的门。

这些门做的是**静态/产物级**检查（不需要真实数据），因此可在任意环境运行；
你把 run.sh 文本、/saisdata 列表、产物 CSV 路径喂进来即可。
"""

from __future__ import annotations

import csv
import re
import zipfile
from collections import Counter
from dataclasses import dataclass, field

from .utility import GateResult


# --------------------------------------------------------------------------- #
# mount-truth / fail-closed 门：Task1 真因的直接检测                            #
# --------------------------------------------------------------------------- #

@dataclass
class MountTruth:
    saisdata_empty: bool
    used_baked_zip: bool
    fail_closed: bool          # 空挂载时是否非零退出/拒绝 fallback
    detail: str = ""

    @property
    def passed(self) -> bool:
        # 真因模式：空挂载 + 用了烤入 zip + 没有 fail-closed -> 就是会 0 分的产物。
        if self.saisdata_empty and self.used_baked_zip and not self.fail_closed:
            return False
        return True


def check_mount_truth(saisdata_listing: list[str], used_baked_zip: bool,
                      fail_closed: bool) -> GateResult:
    empty = len([p for p in saisdata_listing if p.strip()]) == 0
    mt = MountTruth(empty, used_baked_zip, fail_closed)
    if not mt.passed:
        detail = ("空挂载 + fallback 到烤入 /app/benchmark.zip + 非 fail-closed "
                  "—— 正是 Task1 0 分真因；必须改为检测空挂载即退出/等待。")
    elif empty and fail_closed:
        detail = "挂载为空，但已 fail-closed（拒绝 fallback）—— 行为正确。"
    else:
        detail = "挂载真实性 OK。"
    return GateResult("mount_truth", mt.passed, detail)


# 静态扫描 run.sh：是否存在空挂载 fallback 且无 fail-closed guard。
_BAKED_ZIP_RE = re.compile(r"/app/benchmark\.zip")
_EMPTY_CHECK_RE = re.compile(
    r"(-z\s+\"?\$\(ls[^)]*saisdata[^)]*\)|find\s+/saisdata|ls\s+/saisdata)", re.I)
_FAIL_CLOSED_RE = re.compile(r"(exit\s+[1-9]|return\s+[1-9]|set\s+-e)", re.I)
_MOUNT_WAIT_RE = re.compile(r"(until\s+.*saisdata|while\s+.*saisdata|sleep)", re.I)


def check_run_sh(run_sh_text: str) -> GateResult:
    refs_baked = bool(_BAKED_ZIP_RE.search(run_sh_text))
    has_empty_check = bool(_EMPTY_CHECK_RE.search(run_sh_text))
    has_fail_closed = bool(_FAIL_CLOSED_RE.search(run_sh_text))
    has_mount_wait = bool(_MOUNT_WAIT_RE.search(run_sh_text))

    problems = []
    if refs_baked and not (has_empty_check and has_fail_closed):
        problems.append("引用 /app/benchmark.zip 但缺空挂载检测+fail-closed -> 可能偷跑烤入数据")
    if not has_mount_wait:
        problems.append("未见 mount-wait 逻辑（挂载竞态风险，Task2 csv 真因同源）")

    detail = "；".join(problems) if problems else \
        "run.sh：有空挂载检测/fail-closed/mount-wait，行为正确。"
    return GateResult("entry_run_sh", not problems, detail)


# --------------------------------------------------------------------------- #
# 产物完整门：行数/列名/非空/无重复/文件名                                      #
# --------------------------------------------------------------------------- #

@dataclass
class ArtifactSpec:
    required_columns: list[str]
    min_rows: int
    id_column: str | None = None        # 若给定，检查该列无重复
    required_files: list[str] = field(default_factory=list)


def check_csv_artifact(rows: list[dict], spec: ArtifactSpec) -> GateResult:
    problems = []
    if not rows:
        return GateResult("output_artifact", False, "产物为空（0 行）")
    cols = list(rows[0].keys())
    missing = [c for c in spec.required_columns if c not in cols]
    if missing:
        problems.append(f"缺列: {missing}")
    if len(rows) < spec.min_rows:
        problems.append(f"行数 {len(rows)} < 预期 {spec.min_rows}")
    if spec.id_column and spec.id_column in cols:
        dup = [k for k, v in Counter(r[spec.id_column] for r in rows).items() if v > 1]
        if dup:
            problems.append(f"{spec.id_column} 有 {len(dup)} 个重复值")
    detail = "；".join(problems) if problems else \
        f"产物 OK：{len(rows)} 行，列={cols}"
    return GateResult("output_artifact", not problems, detail)


def check_zip_contents(zip_path: str, required_members: list[str]) -> GateResult:
    try:
        with zipfile.ZipFile(zip_path) as zf:
            names = zf.namelist()
            empty = [n for n in names if zf.getinfo(n).file_size == 0]
    except (FileNotFoundError, zipfile.BadZipFile) as e:
        return GateResult("output_zip", False, f"zip 不可读: {e}")
    missing = [m for m in required_members if m not in names]
    problems = []
    if missing:
        problems.append(f"缺成员: {missing}")
    if empty:
        problems.append(f"空文件: {empty}")
    detail = "；".join(problems) if problems else f"zip OK：{names}"
    return GateResult("output_zip", not problems, detail)


def read_csv_rows(path: str) -> list[dict]:
    with open(path, newline="") as f:
        return list(csv.DictReader(f))
