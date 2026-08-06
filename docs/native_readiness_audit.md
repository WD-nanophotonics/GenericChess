# GenericChess Native-Readiness Audit

本审计回答一个问题：**在把规则/搜索热路径 native 化（C/C++/Rust/Cython）之前，瓶颈到底在哪，边界应该画在哪。**

原则：先建立证据，再决定 native 边界；Python Core 保留为 reference oracle。本审计**不实现**
native backend，**不重写 Core**，**不改变正式规则语义**，也不把 instrumentation 永久强制放入正常
搜索热路径（默认完全关闭）。

## 1. 方法

* **可复现 suite**：固定 seed 的规则生成 + 确定性 position mining（合法动作序列重放），
  manifest 为版本化 JSON，记录 RuleSet spec、board size、生成选项、geometry 分类、action
  prefix 与预期类别。
* **两类运行**：
  * normal benchmark：instrumentation 关闭，测真实 NPS / depth / qnode / TT；
  * instrumented audit：注入 `TimingAuditRecorder`，拆分子系统耗时，并单独报告
    instrumentation overhead（smoke 实测约 1%–5%）。
* **Core 微基准**：直接按现有函数边界计时（`_piece_actions` / `_promotion_variants` /
  `_drop_actions` / `_is_legal` / `legal_actions_from_position` / `legal_successors` /
  `position_key` / `_terminal_from_parts` / `pseudo_attacks` 等），不修改 Core。
* **缓存专项**：profile cold / memory-warm / disk-warm 构建时间与序列化大小。
* **分配专项**：在少量代表性 fixture 上运行 cProfile 与 tracemalloc，记录 top functions 与
  allocation sources；`.prof`/trace 只写入 `artifacts/native_readiness/`（gitignore）。

## 2. Suite

* 43 个 RuleSet：30 个生成网格（5 种棋盘尺寸 × 3 种 preset × 2 seed）+ 6 个带偏生成
  （ray-heavy / leap-heavy / long-ray / short-range / hybrid / asymmetric）+ 7 个手工构造
  （multi-promotion / forced promotion / no-drop / restricted drop / sym-leap / ray-sym /
  lance-only low-direction）。
* 每规则集确定性 mining 至多 3 个 position（opening + 最多 2 个非开局类别，偏好较深局面）。
* 分类完全由 compiled movement geometry 得出，不依赖 type_id。
* 全量 suite manifest 提交于 `tests/fixtures/native_readiness_suite_v1.json`（43 rulesets /
  122 positions，棋盘 4–10，movement/promotion/drop 分桶全覆盖）。
* 类别覆盖：opening / midgame / endgame / in_check / multi_evasion /
  low_anchor_escape / immediate_capture / immediate_promotion / near_repetition /
  high_branching / low_branching / drop_available / checking_drop / nonchecking_drop。
  实际覆盖情况见 `docs/performance/native_readiness_latest.json` 的 `suite.categories_*` 与
  `suite.full_suite`（全量 manifest 覆盖）。

## 3. 指标

每 fixture × 预算记录（schema v2）：main_nodes / qnodes / total_nodes / main_nps / q_nps /
total_nps / qnode_ratio / qnode_share / elapsed / depth / TT / fallback / termination reason。
聚合报告 median/min/max，并按 board size 与 movement bucket 分桶。

### Measurement semantics（v2）

* `main_nps = main_nodes / elapsed`；`q_nps = qnodes / elapsed`；
  `total_nps = (main_nodes + qnodes) / elapsed`（用于比较后端总节点速度）；
* `qnode_ratio = qnodes / main_nodes`（可 >1）；`qnode_share = qnodes / total_nodes`（0–1）；
* `SearchLimits.max_nodes` 是 **total-node budget**（`nodes + qnodes`），每 128 个 total
  node 检查一次时间/取消，允许一个检查间隔的越界；
* 旧字段 `nodes_per_second` 保留为 deprecated 别名，等于 `total_nps`；
* timer 口径：`phase_inclusive_seconds`（quiescence = 整棵 qsearch 调用树，main_search =
  wall − quiescence）与 `subsystem_seconds`（direct measured：只统计被包裹的具体函数调用，
  发生在 main search；qsearch 内部不进一步拆分，`subsystem_timing_mode = "direct_measured"`）。

### Qsearch semantics

* 普通非 check 软上限 `quiescence_max_depth`：到上限允许 stand pat / static evaluation；
* 绝对硬上限 `quiescence_hard_max_depth >= quiescence_max_depth`（配置不满足立即报错）：
  check-evasion 也受其约束，到达后 `SearchAborted("qsearch_check_hard_limit")`；
* 被将节点禁止 stand pat、禁止只搜 capture、禁止按 top-K 截断，必须搜索全部解将手；
* 预算耗尽（total/qnode/time/cancel/in-check hard depth）统一通过 `SearchAborted` 中止当前
  iteration，ID 返回上一个完整 depth；depth 1 未完成则走 root scan / 确定性 fallback 并报告
  `completed_depth=0`；
* noisy actions：captures、promotions、immediate terminal actions、checking moves、
  checking drops；普通 non-checking quiet drop 排除并计数。

### Successor experiment（lazy）

* baseline eager path：`legal_successors` 一次生成全部 child（transition + terminal + key）；
* experimental lazy path（`SearchTuning.use_lazy_successors`，默认关闭）：Core 发行
  `LegalSuccessorHandle`（一次合法 movegen，identity-bound 到生成 state），child 仅在真正被
  搜索时 `materialize_legal_successor` 构造；terminal 随 materialize 计算；child position key
  缓存并用于 TT key（`position_key_cache_hits`）；
* legality 仍完全在 Core：handle 只来自官方 legal-action set，AI 不接触 unchecked transition；
* 统计：legal_actions_generated / successor_handles_created / successors_materialized /
  successors_searched / terminal_results_computed / terminal_cache_hits /
  position_keys_computed / position_key_cache_hits。

## 4. 使用

```powershell
# 快速 smoke
.\.venv\Scripts\python.exe -m generic_chess.ai.cli.audit_native_readiness `
  --suite smoke --nodes 1000 --repeats 1

# 正式（分层合并，控制单机运行时间）
.\.venv\Scripts\python.exe -m generic_chess.ai.cli.audit_native_readiness `
  --suite representative --instrument --profiler --nodes 10000 --repeats 1 `
  --positions-limit 4 --max-boardsize 6 --out artifacts/native_readiness/instrumented --no-docs-copy
.\.venv\Scripts\python.exe -m generic_chess.ai.cli.audit_native_readiness `
  --suite representative --nodes 100000 --repeats 1 --positions-limit 6 --max-boardsize 6 `
  --out artifacts/native_readiness/rep100k --merge artifacts/native_readiness/instrumented/audit_summary.json --no-docs-copy
.\.venv\Scripts\python.exe -m generic_chess.ai.cli.audit_native_readiness `
  --suite standard --nodes 10000 --repeats 1 --positions-limit 15 --max-boardsize 8 `
  --out artifacts/native_readiness/latest --merge artifacts/native_readiness/rep100k/audit_summary.json

# 生成 correctness corpus（提交到 tests/fixtures/）
.\.venv\Scripts\python.exe -m generic_chess.ai.cli.audit_native_readiness `
  --generate-correctness-corpus
```

输出：`artifacts/native_readiness/<run>/audit_summary.json`（raw）、
`native_readiness_latest.json`（合并后，含 merge 的版本会同时复制到
`docs/performance/`）、Markdown 报告、可选 CSV 明细、`suite_manifest.json`。

## 5. Native 边界决策框架

根据数据回答（详见最新报告 `docs/performance/native_readiness_latest.md`）：

1. **若 movegen+legality+transition+attack+position key/repetition 合计 ≥ 60–70%** 且单节点
   成本限制完成深度 → 建议一体化 native（state+movegen+make/unmake+hash+TT+recursion）。
2. **若 position key/repetition ≥ 15–20%** 或同一 state 重复算 key → 先做 immutable key
   cache / search hash 与 stable serialization key 分离（不引入 Zobrist）。
3. **若 evaluation ≥ 20–30%**（尤其动态 attack/anchor safety）→ 先做 incremental
   material/hand、fast/exact 分层、bounded lazy full。
4. **若单节点成本低但节点/qnode 爆炸** → 先做搜索消融，C 只能线性加速。

候选方案：

* **方案 1：仅 native rule kernel**（movegen/attack/legality/transition，Python 保留
  AlphaBeta）——FFI 每节点往返与 Python 对象构造开销可能吃掉大部分收益；
* **方案 2：native Core + Python 搜索**（native state/successors/hash）——高频往返仍是风险；
* **方案 3：完整 NativeSearchBackend**（一次调用，native 内含 recursion/TT/eval/hash）——
  收益最大，也是 `SearchBackend` 协议预留的方向。

推荐结论以最新报告为准；本仓库不会仅凭“Python 慢”就决定写 C。

### 本轮结论（2026-08-06 机器实测，见 docs/performance/native_readiness_latest.md）

* 10k tier：total_nps 中位 ~302，qnode_share 中位 ~0.95 —— qsearch 节点占绝对主导；
* instrumented：quiescence phase 占 ~97%，movegen/ordering/TT/position_key 均 <3%；
* 8×8 上 `legal_successors`（含 child 构造）约为裸 movegen 的 4–7 倍 —— per-child
  transition/terminal/key 是主要单节点成本；
* qsearch 修改前后（同一命令）：pathological q-evasion fixture（hybrid）wall 从 ~183s 降到
  ~8s（硬上限/预算语义），但部分 fixture 因不再提前 abort 反而慢 12–35% —— 混合结果，如实记录；
* lazy successor：4 个代表 fixture 上 best action/depth 全部一致，promo/endgame 类 +17–23%，
  其余 ~2% 回退，中位增益 <15% → **保持 experimental、默认关闭**。

### 下一阶段（Native Phase 1）入口

Native Phase 1 应实现：packed state + packed action + compiled movement tables + legal move
generation + make/unmake + attack/check + repetition/hash + perft，并使用现有 correctness
corpus（`tests/fixtures/native_correctness_corpus_v1.json`）做 Python/native differential
testing。本仓库未开始任何 native 实现。

## 6. 已知限制

* 单机单次运行；绝对 NPS 不代表跨机器标准。
* 正式运行采用分层子集（10k 跨尺寸 15 个 position + 100k 代表 4 个 + instrumented/profiler
  4 个）；`requested_budget_tiers` / `completed_budget_tiers` / `executed_*` 明确记录范围。
* instrumented 的 subsystem 为 direct measured（main search 内）；qsearch phase 为 inclusive，
  两者不可直接相加。
* 定向 fixture 已覆盖全部 6 个此前缺失类别（multi_evasion / near_repetition /
  checking_drop / nonchecking_drop / low_anchor_escape / low_branching），predicate 均实测验证。
* lazy successor 为 experimental，未默认启用；启用门槛（中位 ≥15% 且无 >10% 稳定回退）未达到。
