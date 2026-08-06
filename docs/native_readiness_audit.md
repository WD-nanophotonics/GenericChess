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

每 fixture × 预算记录：nodes / qnodes / elapsed / NPS / depth / TT probes/hits/cutoffs /
beta cutoffs / fallback / termination reason / PV 长度 / root legal actions / 平均分支因子。
聚合报告 median/min/max，并按 board size 与 movement bucket 分桶。

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

## 6. 已知限制

* 单机单次运行；绝对 NPS 不代表跨机器标准。
* 完整 standard 10k 在全部 ~110 个 position 上运行过久，正式运行采用分层子集（10k 全量
  受限子集 + 100k 代表子集 + 1M 视耗时决定），实际范围以报告为准。
* instrumented 子系统占比含 qsearch 内部成本；份额用于定位，不代表绝对 NPS。
* 未覆盖类别会在报告中明确列出；不伪造缺失状态。
