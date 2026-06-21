"""提交地址卫生检查器 —— 直接防 21:53 那类 InvalidImageName 事故。

事故复盘：官网提交框里粘进了字面前缀 `Task2  ` / `Task3  `，K8s 把整串当
Docker image name -> `couldn't parse image name "Task2  crpi-...": invalid
reference format` -> InvalidImageName，根本没进入 pull/run 阶段。

铁律（已写入交接规范）：**官网字段只填裸镜像地址，一行一个，不带任务名/表格/
空格/反引号/代码块围栏。** 本模块把这条铁律变成可执行的检查与提取。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# 务实的 Docker image reference 匹配：[host[:port]/]path[:tag][@digest]
# host 段含点或冒号端口；path 段允许 / . _ - ；tag 允许 . _ -
_IMAGE_RE = re.compile(
    r"(?P<ref>"
    r"(?:[a-zA-Z0-9][a-zA-Z0-9.-]*(?::\d+)?/)?"   # 可选 host[:port]/
    r"[a-z0-9]+(?:[._/-][a-z0-9]+)*"               # repo path（小写）
    r"(?::[a-zA-Z0-9][a-zA-Z0-9._-]*)?"            # 可选 :tag
    r"(?:@sha256:[a-f0-9]{64})?"                   # 可选 @digest
    r")"
)

# 常见污染前缀/符号。
_TASK_PREFIX_RE = re.compile(r"^\s*task\s*[123]\s*[:：]?\s*", re.IGNORECASE)
_FENCE_RE = re.compile(r"^```[a-zA-Z]*\s*|\s*```$")


@dataclass
class LintResult:
    raw: str
    cleaned: str | None
    ok: bool
    problems: list[str] = field(default_factory=list)

    def explain(self) -> str:
        if self.ok:
            return f"OK  裸地址可直接粘贴:\n{self.cleaned}"
        head = "REJECT 提交地址不干净，请勿粘贴到官网字段："
        return "\n".join([head] + [f"  - {p}" for p in self.problems] +
                         ([f"  建议裸地址: {self.cleaned}"] if self.cleaned else []))


def is_valid_image_reference(s: str) -> bool:
    """是否为一个 *干净的* 裸镜像地址（整串严格匹配，无空格/前后缀）。"""
    if not s or s != s.strip():
        return False
    if any(c.isspace() for c in s):
        return False
    if "`" in s or "|" in s:
        return False
    m = _IMAGE_RE.fullmatch(s)
    return m is not None


def extract_image_reference(raw: str) -> str | None:
    """从一段可能被污染的文本里提取裸镜像地址（用于自动清洗复制错误）。"""
    text = raw.strip()
    text = _FENCE_RE.sub("", text).strip()
    text = _TASK_PREFIX_RE.sub("", text).strip()
    text = text.strip("`").strip()
    # 若清洗后整串就是合法地址，直接用（保留 @digest 等）。
    if is_valid_image_reference(text):
        return text
    # 否则在文本里搜一个最长的 image-like 子串。
    candidates = [m.group("ref") for m in _IMAGE_RE.finditer(text)]
    candidates = [c for c in candidates if "/" in c and ":" in c]  # 要有 host 和 tag
    return max(candidates, key=len) if candidates else None


def lint_submission(raw: str) -> LintResult:
    """检查一个准备粘进官网提交框的字符串。"""
    problems: list[str] = []
    if raw != raw.strip():
        problems.append("含前导/尾随空白")
    if "\n" in raw.strip():
        problems.append("含换行/多行（官网一次只填一个裸地址）")
    if _TASK_PREFIX_RE.match(raw):
        problems.append("含任务名前缀（如 'Task2 '）—— 正是 InvalidImageName 事故根因")
    if "`" in raw:
        problems.append("含反引号 `")
    if "```" in raw:
        problems.append("含代码块围栏 ```")
    if "\t" in raw or "|" in raw:
        problems.append("含表格分隔符（制表符/竖线）")
    inner = raw.strip()
    if " " in inner and not problems:
        problems.append("地址中间含空格")

    cleaned = extract_image_reference(raw)
    ok = is_valid_image_reference(raw) and not problems
    return LintResult(raw=raw, cleaned=cleaned, ok=ok, problems=problems)
