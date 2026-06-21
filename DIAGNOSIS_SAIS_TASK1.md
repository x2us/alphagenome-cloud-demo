# Task 1 始终零分：深层原因与破零路径

> 用 Gödel Agent（arXiv:2410.04444）的递归自我改进框架，重新审视 SAIS 2026
> 前三个任务，特别是 Task 1 线上恒为 0 的问题。

---

## 0. 环境说明（必须先看）

本仓库是一个**全新的、空的**克隆（除 README 外无任何历史）。容器内**不存在**
你描述的本地 code 记忆库：没有 `/saisdata`、没有 `benchmark.zip`、没有
`result.log`、没有 2,092,260 行 / 117 task 的全量产物、没有 DUD-E/DrugCLIP 代码。
那些文件在你**另一个真实工作区**里，不在这里。

因此本文档做两件**确定能做**的事：

1. 把你的诊断与 Gödel Agent 论文严格对齐，给出可执行的破零顺序；
2. 交付一套**与数据无关、可移植**的"验证器优先"工具（`sais/`），你可以原样
   拖进真实工作区接上真实数据。需要真实文件才能做的步骤（如"配置实测门"读
   `result.log`），我已标注出来，需要你把文件带到能访问的环境或贴出来。

---

## 1. 核心结论：U 写反了，不是算法不够聪明

**Task 1 恒为 0 的深层原因，是整个递归改进循环的效用函数（utility）错了。**

Gödel Agent 的关键不是"让智能体乱改自己"，而是：每一次自我修改都必须由**环境
效用函数**裁决，并且能在修改变坏时**回退**（论文消融实验证明 Reflection 与
Error Handling 影响最大）。其循环是：

```
self_inspect → interact → self_update → continue_improve
π_{t+1}, I_{t+1} = I_t(π_t, I_t, r_t, g)
```

此前的错误在于把效用近似成了"线上分数变高"。但线上 grader 对 Task 1 是
**乘法门控、fail-closed** 的：只要任一硬门（入口契约 / 输出产物 / 反作弊 /
日志真实性）不过，分数直接置 0，模型再好也是 0。于是在 Gödel Agent 看来，
**适应度景观在 0 处完全平坦** —— 每一个候选都得 0 —— 循环拿不到任何梯度，
永远爬不出来。这与本仓库玩具复现里 `is_suspicious_zero` 标志要表达的是同一件事：

> **gated zero（管道/反作弊门控的 0）≠ skill zero（模型真的不会做）。**
> 把前者当成"有效的低效用"去调模型，是无尽零分的根源。

**正确的 U（已在 `sais/utility.py` 实现）：**

```text
U = 入口契约通过          (0/1)
  × 输出产物通过          (0/1)
  × 反作弊硬门通过        (0/1)   ← external reconstruction 等会直接置 0
  × 日志真实性通过        (0/1)
  × 本机官方代理分提升    (连续，Mean EF1% 的"提升量"，而非绝对值)
```

前四项任一为 0，则 U=0，且**记录是哪一个门把它置零的**。`sais/demo.py` 跑出来
的就是这个：一个 hard-boost/answer-recovery 候选，本机 naive EF1% 高达 20.0，
却因反作弊门 + 日志真实性门双双 FAIL → **GATED ZERO**；一个 clean 候选全门通过
→ U>0。

---

## 2. Task 1 零分根因排序（沿用你的证据分级）

### PROVEN（已证）
- 结果**行数/格式本身不是主因**：已有 2,092,260 行、117 task 的本机全量产物。
- 官方规则对齐文件写明 Task 1 可将 `benchmark.zip` 烤入镜像，读
  `/app/benchmark.zip` **未必是 bug**。
- 出货 artifact 实测 `inchikey_boost=True, exact_tiebreak=True`，且有 22,566 行
  `score≥0.9999`，86/102 个 DUD-E 靶点饱和**超 top 1% 预算** ——
  这是**强答案恢复 / 外部重构指纹**。（→ `sais/anticheat.py` 正是检测它的）
- 代码内部用 Mann-Whitney `_auc` 选 alpha，日志却声称 `Metric: Mean EF1%` ——
  **自治日志真实性失配**。（→ `sais/log_truth.py` 正是检测它的）

### HYPOTHESIS（待证，需真实环境）
- 线上 0 的**最高嫌疑是反作弊/答案恢复置零**，其次才是 mount / 空
  `/saisdata` / fallback 触发。
- 若 r3 fail-closed 证明确为空挂载 → 先修平台协议；
  若输入正常仍 0 → **立刻切 clean no-refs / no-target-map / no-hard-saturation 路线**。

### NO-GO（明令禁止）
- 不再提交 refs-family / skeleton hard-boost 家族。
- 不再用线上 0/非 0 反复调参（那是在污染 U）。
- 不再把 `score_after_integrity_penalty` 或 `suspicious_flag` 当排名目标；
  真正致命的是 **hard flags，尤其 external reconstruction**。

---

## 3. Task 1 具体破零路径（执行顺序）

> 原则：**先改 verifier，再改候选；先破 0，再冲榜。** 与 Gödel Agent 论文的
> "效用先于策略"一致。

1. **配置实测门（需真实 artifact）** —— 回拉/本地运行候选，确认 `result.log` 里
   **真实**是 `inchikey_boost=False, exact_tiebreak=False`，**不能只看源码**。
   工具：`sais/log_truth.check(log_text, executed_config)`，其中 `executed_config`
   必须来自**真实运行的插桩输出**，不是读源码。
2. **修日志真实性** —— 日志必须声明**真实优化目标**（held-out reference AUC 或
   真正的 EF1 proxy），不能声称未执行的 Mean EF1%。
3. **新建 Task 1 本机 Mean EF1% harness** —— 用公开 DUD-E actives/decoys；
   **排除同靶 DUD-E active 进入 refs**，避免自欺骗式高估。
   工具：`sais/ef1.mean_ef1(...)`，对同靶泄漏会直接 `ReferenceLeakageError`。
4. **候选必须同时过**：入口 + 行数 + zip + 反作弊饱和预算 + 日志真实性 + EF1% 预测门。
   工具：`sais/utility.evaluate(hard_gates, proxy_gates)`，乘法 + fail-closed。
5. **破 0 之后**再做 top-k mean / LIT-PCBA seam / top-band DrugCLIP 结构重排。
   结构重排目前是 **HOPED**，不是可交方案（吞吐未实测、two-stage rerank 代码
   尚不存在）—— 不要在破 0 前投入。

---

## 4. Task 2 / Task 3 连带结论

**Task 2**：先修**评分器元规则**。6:4 与 7:3 口径冲突仍在，必须做**双口径敏感性**
分析，先复现线上 0.660，再谈 k64/r3 是否真实提升。公开依据支持
**Vina + SA + route/starting-material**，而不是 QED/diversity 自创代理。

**Task 3**：别再相信"ESMFold 必赢"或"几何格式修完就冲榜"。几何非零只是**地板**；
下一步严格 **parser / sequence / physics / metric gate**，再做高质量锚结构 +
小幅物理合理 ensemble。

---

## 5. 与 Gödel Agent 论文的逐条映射

| 论文要素 | 本项目对应 | 代码 |
|---|---|---|
| 环境效用函数裁决每次修改 | 验证器优先的乘法门控 U | `sais/utility.py` |
| Reflection（先想再改） | 从失败签名判定 gated-zero vs skill-zero | `godel_agent/agent.py::reflect` |
| Error Handling + 回退 | 候选 trial-apply，不提升即 rollback | `godel_agent/agent.py::self_update` |
| 平坦 0 景观→无梯度 | `is_suspicious_zero` / `is_gated_zero` | `godel_agent/harness.py`, `sais/utility.py` |
| 自指：改"如何改" | 智能体替换的是 extractor（元规则），不是答案 | `godel_agent/agent.py` |

**与 Schmidhuber 哥德尔机的差异（也是风险）**：Gödel Agent 用"环境适应度"代替
"先验全局效用证明"，是经验主义的进化选择，因此**会陷局部最优**。对 SAIS 的含义：
本机 EF1% proxy 只是适应度近似，若 proxy 被自己污染（同靶泄漏 / 反作弊指纹），
就会爬到"线上 0"的伪峰。所以 proxy 的**诚实性**（§3 步骤 3）比 proxy 的高低更重要。

---

## 6. 公开依据

- Gödel Agent: https://arxiv.org/abs/2410.04444
- DrugCLIP: https://arxiv.org/abs/2310.06367
- DUD-E FAQ: https://dude.docking.org/faq
- AutoDock Vina: https://pmc.ncbi.nlm.nih.gov/articles/PMC3041641/
- AiZynthFinder: https://pmc.ncbi.nlm.nih.gov/articles/PMC7672904/
- PoseBusters: https://pmc.ncbi.nlm.nih.gov/articles/PMC10901501/
- AlphaFlow: https://arxiv.org/abs/2402.04845

---

## 7. 我需要什么才能继续做"数据相关"步骤

要把 §3 的步骤 1–3 从"工具就绪"变成"在你真实数据上跑出结论"，需要其一：

- 在**能访问真实 SAIS 工作区**的环境里运行我（容器需挂载该工作区）；或
- 把以下文件贴出/带过来：`result.log`、Task 1 评分/入口代码、提交产物样例
  （前若干行 + 含 `score≥0.9999` 的若干行）、官方规则对齐文件。

拿到后我会：跑配置实测门核对 boost 真实开关、用公开 DUD-E 建无泄漏 EF1% harness、
把你的提交过一遍反作弊自审，给出"是该修平台协议还是该切 clean 路线"的判定。
