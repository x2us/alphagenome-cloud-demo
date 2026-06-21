# 今晚执行交接 Runbook（交给真实 SAIS 工作区）

> 目标：**先合法破零，再冲分。** 顺序铁律：`先改 U → 再改 I → 最后改 π`。
> 配套：[`DIAGNOSIS_SAIS_TASK1.md`](DIAGNOSIS_SAIS_TASK1.md) ·
> [`WORKFLOW_GODEL.md`](WORKFLOW_GODEL.md)。本文件是可独立执行的清单。
>
> 前置：真实工作区需有真实代码/数据/Docker/GPU（本验证器仓库无数据，仅提供门）。
> 先 `pip install -e .` 不需要——`sais/` 纯标准库，把本仓库目录加进 `PYTHONPATH` 即可。

---

## A. G0 真相源（只认这些，其余降级历史）
官方规则 · 本地 release card · pull-back artifact · 完整线上日志 · 评分器输出。
旧 handoff / 旧推荐地址 / 无 release card 的地址 = 历史信息，不得作为依据。

## B. 提交纪律（必读，防 21:53 事故复发）
官网字段**只填裸镜像地址，一行一个**，不带任务名/表格/空格/反引号/围栏。
**每个要提交的地址先过 linter：**
```python
from sais.submission import lint_submission
r = lint_submission(ADDR)          # ADDR 为准备粘贴的整串
assert r.ok, (r.problems, r.cleaned)   # 不 ok 就用 r.cleaned，别手粘
```
当前推荐裸地址（已过 linter）：
```text
crpi-rwdagqllzc5mssc6.cn-shanghai.personal.cr.aliyuncs.com/sais-cns-2026/sais-cns-task1-drugclip:anti-recon-cap985-mountwait-failclosed-20260619-r3
crpi-rwdagqllzc5mssc6.cn-shanghai.personal.cr.aliyuncs.com/sais-cns-2026/sais-cns-task2-molecule:sbdd-k64-pool8-t20-div035-mountwait-csvfix-20260619-r3
crpi-rwdagqllzc5mssc6.cn-shanghai.personal.cr.aliyuncs.com/sais-cns-2026/sais-cns-task3-conformation:geometric-physfix-mountwait-20260619-r2
```

---

## C. Task1 破零（最高优先级）

### 阶段 A — 裁决 0 分根因（先做，不动算法）
- **动作**：读最新线上日志，确认是空挂载 fallback，还是跑完仍 0。
- **工具**：
  ```python
  import os
  from sais.contract import check_run_sh, check_mount_truth
  print(check_run_sh(open("run.sh").read()).detail)
  print(check_mount_truth(os.listdir("/saisdata"),
                          used_baked_zip=True,   # 由日志/代码实测得到
                          fail_closed=False).detail)
  ```
- **分支**：
  - 空挂载/入口问题 → 只修 `mountwait + fail-closed + zip-stage`，**不动算法**。
    （r3 镜像已做此修复，先验证它在真实挂载下产物正确。）
  - 输入正常仍 0 → 判定 2D refs / skeleton hard-boost 家族高危 → 进阶段 B clean 路线。
- **验收**：`check_run_sh` 与 `check_mount_truth` 均 `passed=True`。

### 阶段 B — clean 2D 地板（必做，破零核心）
产出一个 artifact，**实测**（不是看源码）满足全部：
- `inchikey_boost=False`、`exact_tiebreak=False`、不使用 `target_map`
- skeleton match 不饱和到 1.0；`score>=0.9999` 饱和数降到安全区
- 日志不再声称 `Mean EF1%` 而实际优化 `_auc`
- **工具（配置实测门 + 反作弊自审）**：
  ```python
  from sais.log_truth import check
  from sais.anticheat import audit
  executed = {"metric": "...", "inchikey_boost": False, "exact_tiebreak": False}  # 来自真实运行插桩
  assert check(open("result.log").read(), executed).passed
  a = audit(scores, target_of_row, known_active_ids, row_ids)
  assert a.passes_hard_gate, a.explain()      # 无饱和/无外部重构指纹
  ```
- **验收**：log_truth 一致 + anticheat 硬门绿 + 阶段 A 门绿。

### 阶段 C — Task1 本机 EF1% harness（必做，给真实梯度）
- 用公开 DUD-E actives/decoys；**该靶自己的 DUD-E actives 必须从 refs 排除**。
- 分开报告 DUD-E 与 LIT-PCBA proxy。
- **工具**：
  ```python
  from sais.ef1 import TargetScores, mean_ef1
  targets = [TargetScores(t, labels, scores, ids, reference_ids=refs_excluding_same_target)
             for ...]
  res = mean_ef1(targets)        # 同靶泄漏会直接 ReferenceLeakageError
  ```
- **接受门**：预测提升 > margin（建议 EF1% 绝对提升 ≥ 0.5 且非负全靶），且反作弊硬门通过。

### 阶段 D — 冲分（破零后才做）
top-k mean 替代 max similarity · LIT-PCBA seam 单独优化 · 只对 top 1–2% 做 DrugCLIP
结构重排（**先实测吞吐**，不引用未证的 34 lig/s）。结构重排现状 = HOPED，未破零前不投入。

---

## D. Task2（先修评分器，不先冲新分子）
1. 建**双口径 scorer**：6:4 与 7:3 同时输出（项目内官方材料口径冲突）。
2. 用已知线上 `0.660132` 的 artifact 做校准，先复现该分。
3. **只有两口径都显示稳健提升**才允许进候选。
4. 候选方向：route-valid + stock-aware + 逐分子 Vina redock。
   `k64/div035` 这类小 proxy 在未过官方 scorer 前一律视为噪声。
- **验收**：双口径均较 0.660132 提升 + 产物门绿（`check_csv_artifact`/`check_zip_contents`）。

## E. Task3（几何版只是地板）
1. **strict parser gate**：Gemmi/Biotite/mdtraj、`model_num`、chain、CA 数、sequence 对齐。
2. **physical gate**：clash、断链、CA 距离、Ramachandran/几何 sanity。
3. **再** metric-aware ensemble：高质量 anchor + 小幅物理合理扰动。
   不再盲信 ESMFold/ANM 必赢，也不盲信多样性越大越好。
- **注意**：model_num 解析真因目前是**强嫌疑非事实**，先把 parser gate 在真实 gemmi/biotite
  下跑通再下结论。

---

## F. 候选准入（G1–G3，每个 task 通用）
用状态机统一裁决，避免主观：
```python
from sais.pipeline import Pipeline, Candidate
from sais.release_card import ReleaseCard
P = Pipeline()
cand = Candidate(
    cid="task1-r4", task="task1", parent_cid="task1-r3",
    single_factor="boost-off",          # 只改一个因子；多因子会被 REJECT
    hard_gates=[g_entry, g_output, g_anticheat, g_mount, g_logtruth],  # 均为 GateResult
    proxy_score=local_ef1_mean,         # 本机代理分，越高越好
    release_card=ReleaseCard(image_digest="sha256:...", image_reference=ADDR,
                             pullback_verified=True, smoke_passed=True,
                             log_summary="...", single_factor="boost-off",
                             parent_digest="sha256:..."),
)
v = P.review(cand)                      # ADMIT / REJECT / ROLLBACK
print(v); print("可提交:", P.submittable("task1") and P.submittable("task1").release_card.image_reference)
```
**只有 ADMIT 的候选才允许去官网提交，且提交前再过一次 `lint_submission`。**

---

## G. 今晚最小动作清单（按优先级）
1. **[Task1 破零]** 真实挂载下验证 r3：阶段 A 两门绿 → 阶段 B clean artifact 实测 boost off /
   饱和下降 / 日志真实性 → 阶段 C 跑通 DUD-E public subset EF1% harness。
2. **[Task2]** scorer 改 6:4/7:3 双口径并复现 0.660132；未复现前不提交新分子候选。
3. **[Task3]** 在真实 gemmi/biotite 下跑 strict parser gate + physical gate；只交过门版本。
4. **[纪律]** 每个候选附 release card；每个提交地址过 `lint_submission`；每轮只改一个因子。
5. **[审查]** 候选生成后做只读 Gödel 审查：改了哪个假设、用什么 verifier 证明、有无新硬门风险；
   无证据不进提交队列。

> 验证器仓库分支：`claude/godel-agent-research-nq5pw1`。把目录加进 `PYTHONPATH` 后
> `python tests/test_all.py` 应 22/22 通过，确认门逻辑可用，再接真实数据。
