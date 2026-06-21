# Gödel 总控工作流（v2，本轮交叉验证后）

> 配套诊断见 [`DIAGNOSIS_SAIS_TASK1.md`](DIAGNOSIS_SAIS_TASK1.md)。
> 本文件记录**本轮确认的真因更新、提交事故教训、G0–G3 工作流、六代理分工**，
> 以及"哪些能在本容器交付 / 哪些需真实工作区"。

---

## 0. 本轮真因更新（PROVEN / 降级）

### Task1 —— 0 分真因已定死（PROVEN）
线上 `/saisdata` 是**空目录**，旧 `run.sh` fallback 到 `/app/benchmark.zip`，
随后跑了 117 tasks / 2,092,260 行。**它确实跑完了，但跑的是烤入样本而非真实挂载
数据，所以 0 分合理。** 修法：空挂载必须 **fail-closed**（检测到即退出/等待挂载），
绝不偷偷 fallback 跑完。→ 已编码为 `sais/contract.check_mount_truth` /
`check_run_sh`，并有测试 `test_mount_truth_*` / `test_run_sh_*`。

### Task2 —— `No columns to parse from file`（PROVEN 同源）
高度符合挂载竞态 / CSV 协议问题。r3 镜像已实测：空挂载下仍生成非空
`result.csv`、`result1..3.csv` 且均进 zip。→ 产物门 `sais/contract.check_csv_artifact`
/ `check_zip_contents`。

### Task3 —— 降级为"未复现假设"
"strict_parse_gate 自测通过 / biotite 复现 model_num 拒绝"**本环境未复现**
（host 与远端 r2 镜像均缺 `gemmi`/`biotite`）。model_num 解析真因仍是**强嫌疑、
非已验证事实**。当前 Task3 仅几何地板 + mount-wait，不是冲分折叠版。

---

## 1. 提交事故教训（已编码为 linter）

21:53 两次失败**不是镜像跑挂**，而是提交框粘进了字面前缀 `Task2  ` / `Task3  `：

```
couldn't parse image name "Task2  crpi-...": invalid reference format  -> InvalidImageName
```

K8s 把整串当 image name，根本没进 pull/run。**铁律：官网字段只填裸镜像地址，
一行一个，不带任务名/表格/空格/反引号/围栏。** → `sais/submission.lint_submission`
拦截并自动清洗；本轮三个裸地址已全部实测 `OK`。

### 本轮推荐提交地址（已过 linter，可直接粘贴，一行一个）

Task1：
```text
crpi-rwdagqllzc5mssc6.cn-shanghai.personal.cr.aliyuncs.com/sais-cns-2026/sais-cns-task1-drugclip:anti-recon-cap985-mountwait-failclosed-20260619-r3
```
Task2：
```text
crpi-rwdagqllzc5mssc6.cn-shanghai.personal.cr.aliyuncs.com/sais-cns-2026/sais-cns-task2-molecule:sbdd-k64-pool8-t20-div035-mountwait-csvfix-20260619-r3
```
Task3：
```text
crpi-rwdagqllzc5mssc6.cn-shanghai.personal.cr.aliyuncs.com/sais-cns-2026/sais-cns-task3-conformation:geometric-physfix-mountwait-20260619-r2
```

---

## 2. 核心原则：先 U → 再 I → 最后 π

```text
先改 U(效用函数) → 再改 I(改进规则) → 最后才改 π(候选算法/镜像)
```
即：先证明什么算"值得保留的改动"，再让构建侧执行候选开发。

## 3. G0–G3（已编码为 `sais/pipeline.Pipeline`）

- **G0 冻结真相源**：只有带 release card + pull-back 的候选算真相，其余降级历史。
- **G1 元验证器优先**：候选必须过全部硬门 + 给出**本机代理分**（不是线上分）：
  入口契约 / 产物完整 / 合规硬门 / mount-truth / release card。
- **G2 单因子递归改进**：每轮只改一个因子；失败回滚，不混合修复（多因子直接 REJECT）。
- **G3 提交前 Gödel 审查**：全门绿 + release card 齐全 + 单因子可定因，才进提交队列。

`Pipeline.review(candidate)` 返回 `ADMIT / REJECT / ROLLBACK`，并维护每个 task 的
当前最优可提交候选。

## 4. 六代理分工

| 代理 | 职责 |
|---|---|
| Gödel | 元规则总控，审查 verifier 是否先于候选 |
| McClintock | Task1 生物/虚筛证据（DUD-E/LIT-PCBA/DrugCLIP） |
| Newton | Task2 数值评分器（Vina/SAScore/route 分解） |
| Parfit | 合规与反作弊（答案恢复、日志真实性） |
| Locke | 提交契约、release card、pull-back、入口协议 |
| Confucius | 交接摘要，压缩为可执行清单 |

---

## 5. 执行单：本容器可交付 vs 需真实工作区

### ✅ 本容器已交付（纯逻辑、可测、可移植）
- 提交地址 linter（防 InvalidImageName）—— `sais/submission.py`
- mount-truth / run.sh fail-closed 门（Task1 真因）—— `sais/contract.py`
- 产物完整门 / zip 门 —— `sais/contract.py`
- release card 规范与门 —— `sais/release_card.py`
- G0–G3 候选队列状态机 —— `sais/pipeline.py`
- 反作弊自审 / 日志真实性 / EF1% proxy（上一轮）—— `sais/{anticheat,log_truth,ef1}.py`
- 全部 22 项测试通过

### ⛔ 需真实工作区 / 真实数据（本容器做不了）
- Task1：产出 clean 2D artifact，**实测** boost off / 饱和下降 / 日志真实性修复
- Task1：补 EF1% harness 跑 public DUD-E subset（需下载数据，本容器出网被墙）
- Task2：scorer 改 6:4/7:3 双口径并**复现 0.660132**（需真实 scorer + artifact）
- Task3：严格 parser/physics gate 跑通（需 gemmi/biotite + 真实结构）
- 任何 pull-back / smoke / digest（需 Docker + 镜像仓库访问）

> 要推进 ⛔ 部分：把我接进能挂载真实工作区的环境，或贴出
> `result.log` / Task1 入口与评分代码 / 产物样例 / 官方规则对齐文件。
