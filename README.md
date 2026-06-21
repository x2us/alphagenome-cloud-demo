# Gödel Agent × SAIS 2026 — 验证器优先的破零框架

基于 **Gödel Agent**（[arXiv:2410.04444](https://arxiv.org/abs/2410.04444)）的递归
自我改进思想，攻坚 SAIS 2026 前三个任务，重点解决 **Task 1 线上始终 0 分**。

核心结论：**Task 1 恒为 0 不是缺少更聪明的算法，而是递归改进循环的效用函数 U 写反了。**
完整分析见 **[`DIAGNOSIS_SAIS_TASK1.md`](DIAGNOSIS_SAIS_TASK1.md)**。

> 注：本仓库是全新空克隆，**不含**真实 SAIS 数据/产物（`/saisdata`、`result.log`
> 等不在本容器）。这里交付的是**可移植**的验证器工具 + 诊断，可拖进真实工作区使用。

## 两部分

### 1. `godel_agent/` — 论文复现 + 最小"零分"复现
一个紧凑、可运行的 Gödel Agent 循环（`self_inspect → interact → self_update →
continue_improve`，含 Reflection 与 Error-Handling/回退），以及一个三赛道玩具：
某赛道因**上游解析/契约 bug** 恒为 0，而非模型不会做。

```bash
GODEL_BACKEND=stub python run.py          # Track 1 = 0（all-unparseable，被标 SUSPICIOUS ZERO）
GODEL_BACKEND=stub python run.py --agent  # 智能体自动修复 verifier → 100%
```

它演示了 SAIS 的同构教训：**效用被上游门控置 0 → 景观平坦 → 再强的模型也爬不出 0。**

### 2. `sais/` — 验证器优先的效用 U（真实交付物）
把本机效用做成线上 grader 的**忠实、fail-closed 乘法代理**：

```text
U = 入口契约 × 输出产物 × 反作弊硬门 × 日志真实性 × 本机 EF1% 提升
```

```bash
python -m sais.demo   # 对比：作弊候选→GATED ZERO；clean 候选→U>0
```

- `sais/utility.py` — 乘法门控 U，区分 gated-zero 与 skill-zero
- `sais/ef1.py` — 诚实的本机 Mean EF1% proxy（同靶泄漏直接报错）
- `sais/anticheat.py` — 饱和预算 / 外部重构指纹自审（避开会被置 0 的 hard flags）
- `sais/log_truth.py` — 日志声称 vs 实测配置一致性（boost 开关 / metric）
- `sais/submission.py` — 提交地址 linter，防 `InvalidImageName`（21:53 事故）
- `sais/contract.py` — 入口契约 / 产物完整 / **mount-truth fail-closed 门**（Task1 真因）
- `sais/release_card.py` — release card 规范（digest/pull-back/smoke/单因子）
- `sais/pipeline.py` — G0–G3 候选队列状态机（ADMIT/REJECT/ROLLBACK）

## 总控工作流
G0 冻结真相源 → G1 元验证器优先 → G2 单因子递归改进 → G3 提交前 Gödel 审查。
详见 **[`WORKFLOW_GODEL.md`](WORKFLOW_GODEL.md)**（含本轮真因更新、提交事故教训、
六代理分工、当前推荐裸地址）。

## 测试
```bash
python tests/test_all.py   # 11/11
```

## 公开依据
Gödel Agent · DrugCLIP · DUD-E · AutoDock Vina · AiZynthFinder · PoseBusters · AlphaFlow
（链接见 `DIAGNOSIS_SAIS_TASK1.md` §6）
