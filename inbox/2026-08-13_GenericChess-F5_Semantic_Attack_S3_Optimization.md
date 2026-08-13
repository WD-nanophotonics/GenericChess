# Inbox record

- Received: `2026-08-13T07:37:59-04:00`
- Subject: `GenericChess — F5: Semantic Attack / S3 Legality Runtime Optimization`
- From: `W D <icywoods.1@gmail.com>`
- Gmail message reference: `19ffaea337ecd52a`
- Attachment: `GenericChess_F5_Semantic_Attack_S3_Optimization.md` (`18913` bytes)
- Status: `ACTIVE — authoritative task captured before execution`
- Local source: this file contains the complete attachment text; do not overwrite it with a later summary.

# GenericChess — F5: Semantic Attack / S3 Legality Runtime Optimization

你现在在：

- Repository: `WD-nanophotonics/GenericChess`
- Worktree / branch: `sandbox`
- Authoritative starting `origin/sandbox`:
  `363c74dc94217941f67edfbcfcd1bb84432f96a0`
- `origin/master`:
  `4f1d03a308f5fd04a01bbd980c7411888ea1ed9d`
- `origin/chat`:
  `d6b0d5720efe23019a7a2b4cce72e05beee2e6c4`

F4 已正式 closure：

- `F4_RESULT = OPTIMIZATION_PASS`
- H4A harness: `98ecd8c400157984df809f23a988120dfa5dca16`
- H4B optimization: `1cc19b4d0e92dfd36871a228cb628a906e4b1759`
- E4 evidence: `363c74dc94217941f67edfbcfcd1bb84432f96a0`

F4 已证明：

- fixed-node checkpoint dispatch 是第一主热点，并已通过一个局部 fast path 修复；
- Semantic Standard Shogi Profile A aggregate median: `6479.636 ms -> 4748.891 ms`，约 `26.7%` 提速；
- Profile B aggregate median: `38329.638 ms -> 25295.268 ms`，约 `34.0%` 提速；
- F4 后剩余最重要的热点是：
  1. semantic attack/check；
  2. S3 legality trials / own-anchor safety；
  3. semantic runtime push / terminal；
  4. qsearch 中上述成本的放大。

本轮是 **F5 Semantic Attack / S3 Legality Runtime Optimization**。

本轮不是棋力调参，不是 Native migration，不是 TT redesign，不是 evaluator work。

---

# 0. 本轮唯一目标

在完全保持 Semantic ruleset correctness、action identity、action order、transition、S3/S4 semantics、history/repetition、TT、interactive cancellation contract 不变的前提下：

> 显著降低 Semantic Standard Shogi 中 `is_square_attacked / in_check / S3 own-anchor safety` 以及其直接 candidate-dispatch 成本。

本轮首先必须证明具体重复工作在哪里，然后只允许实施一个 coherent optimization family。

如果没有任何候选通过 correctness + materiality gate：

```text
F5_RESULT = AUDIT_ONLY_PASS
```

合法结束。

不要为了必须优化而修改架构。

---

# 1. Baseline gate

开始前 hard assert：

```text
origin/sandbox ==
363c74dc94217941f67edfbcfcd1bb84432f96a0

origin/master ==
4f1d03a308f5fd04a01bbd980c7411888ea1ed9d

origin/chat ==
d6b0d5720efe23019a7a2b4cce72e05beee2e6c4
```

并：

```text
HEAD == origin/sandbox
sandbox tracked worktree clean
```

如果 sandbox 已被其他任务推进：

```text
BASELINE_MOVED
STOP
```

禁止 reset、force push、覆盖其他任务、修改 master、修改 chat。

---

# 2. F3 / F4 invariants 全部冻结

## 2.1 F3 TT / history correctness

禁止修改：

```text
RuntimeHistoryContext semantics
continuous_check_loss TT eligibility
opaque/incomplete history fail-closed
RuntimeCountsSnapshot exact guard
RuntimeHash authority model
history-context digest authority model
TT bounds
TT generation
TT replacement
mate score normalization
qsearch TT policy
```

RuntimeHash / digest 仍然只允许作为 discriminator。
Exact identity / exact context equality 仍是 authoritative collision guard。

## 2.2 F4 checkpoint contract

禁止回退或扩张 F4 optimization。

当前 `_Context.checkpoint`：

- fixed-node non-interactive path 保留 direct node-budget check；
- interactive cancellation / wall-clock deadline path 必须保持原 cooperative semantics。

不得通过减少 checkpoint coverage、跳过 semantic work-unit checkpoint、降低 cancellation responsiveness 换性能。

F5 的性能收益必须来自减少实际 semantic work，不是重新削弱 interruptibility。

---

# 3. Core / Search 边界

Core 继续 AI-unaware。

严禁：

```text
Core import AlphaBeta
Core import SearchLimits
Core import SearchStatistics
Core import AuditMetric
Core 读取 AI tuning
Core 读取 wall-clock deadline
```

允许：

- 纯 semantic executor 内部私有索引；
- 纯 position-local / engine-local 派生结构；
- generic cooperative `checkpoint: Callable[[], None] | None`；
- standalone profiling/microbenchmark；
- test-only instrumentation；
- AI-side audit recorder。

如果需要给 Core 加 instrumentation，必须是完全 generic、默认关闭、不会引入 AI dependency；但本轮优先避免。

---

# 4. 先建立 F5 harness，不准先优化

先创建 reproducible harness，例如：

```text
scripts/audit_f5_semantic_attack_s3.py
```

并建立对应 tests。

Harness commit：

```text
H5A
```

必须：

```text
parent = 363c74...
H5A = harness/tests/docs only
NO production optimization
```

push `origin/sandbox = H5A` 后才允许测 baseline。

---

# 5. Certified Semantic Shogi authority

所有正式 Semantic Shogi measurements 必须：

```python
compiled = compile_semantic_ruleset(
    build_semantic_shogi_ruleset()
)
```

hard assert fingerprint：

```text
5b3d04eda31a342b729fc9af8a04cdde13c796646b2b37024891f8c99703c345
```

禁止 benchmark-local Shogi legality patch、legacy RuleSet authority、cshogi 代替 production legality、修改 certified ruleset、修改 public serialization / fingerprint。

---

# 6. Deterministic corpus

复用 F4 corpus，不重新发明长 benchmark。

Generic controls：

```text
legacy draw control
continuous_check_loss control
```

Semantic Shogi 至少 4 个：

```text
reachable
deterministic
nonterminal
legal history preserved
```

优先直接复用 F4 的 plies `0/1/2/3` prefixes / deterministic seeds。

此外为 attack/S3 microbenchmark 新增 deterministic query corpus，至少覆盖：

1. 当前 side anchor 不被攻击；
2. 当前 side anchor 被攻击；
3. sliding attacker；
4. leaper attacker；
5. blocker 阻挡 ray；
6. capture geometry；
7. promoted piece movement；
8. drop-related position；
9. candidate move 造成 discovered attack；
10. candidate move 解除 check；
11. candidate move 暴露 own anchor；
12. S4-bearing pattern 仍然贡献 pseudo-attack 的 regression witness。

不要求每个 fixture 都是完整 Shogi opening；但正式 performance corpus 必须含 certified Semantic Standard Shogi。

---

# 7. 先量化 attack/S3 的真实重复工作

必须给出 baseline counters / call distribution。

## 7.1 `is_square_attacked`

每次/总体记录或可靠推导：

```text
attack queries
patterns visited
type ids visited
board slots inspected
pieces inspected
owner-matching pieces
type-matching pieces
geometry ids inspected
geometry candidates generated
target matches
path checks
guard checks
successful attack early exits
failed full scans
```

如果不能直接无侵入计数，可以用 cProfile call graph、deterministic wrapper、test-only monkeypatch、local microbenchmark instrumentation。

不要污染 production hot path 只为了得到统计。

## 7.2 `in_check`

记录：

```text
in_check calls
own-anchor lookup calls
attack queries triggered
```

确认 `_own_anchor` 是否 material；若不是，明确排除。

## 7.3 S3

至少记录：

```text
S0/S1 candidates
S3 trial transitions
S3 accepted
S3 rejected
own_anchor_safe checks
squares_not_attacked checks
attack queries caused by S3
```

## 7.4 Search-level attribution

在 F4 Profile A/B 上重新记录：

```text
wall
nodes/qnodes
MOVE_GEN
QUIESCENCE
runtime push
EVALUATION
TT
```

并补 F5 attack/S3 counters。

---

# 8. 必须审计当前算法形态

当前 `SemanticEngine.is_square_attacked()` 的形态大致是：

```text
for pattern
  for type_id
    scan full position.board
      if matching piece
        for geometry
          for geometry candidate
            if candidate target == queried square
              path/guard
```

当前 `_iter_board_candidates()` 也存在：

```text
for pattern
  for type_id
    scan full position.board
```

F5 必须证明以下至少哪一种是 material：

A. 同一 position 中反复 full-board scan；
B. pattern × type 的重复 dispatch；
C. incompatible geometry 的重复过滤；
D. attack query 为了一个 fixed target 生成大量无关 target；
E. S3 对大量候选重复调用 full semantic attack scan；
F. anchor lookup；
G. 其他由 profile 发现的直接原因。

不要在没有 evidence 的情况下声称其中任何一个是主因。

---

# 9. 允许的 optimization family

本轮只允许一个 coherent family：

```text
Semantic candidate / attack dispatch reuse
```

它可以由一组紧密相关、共同目的的局部改动组成，但必须是同一个 abstraction，不允许趁机做第二类优化。

推荐优先级如下，但以证据决定。

## Option A — position-local source/type index

概念上：

```text
one board scan
→ sources_by_owner_and_current_type
```

随后：

```text
pattern/type loop
→ lookup matching sources
```

而不是每个 pattern/type 重扫整个 board。

必须保持：

```text
pattern order
type order
source order
geometry order
promotion order
public action order
```

exact parity。

该 index 必须：

- position-local；
- 不改变 Position；
- 不改变 public hash/fingerprint；
- 不产生 stale cache；
- 不依赖 Shogi 特例。

## Option B — immutable semantic dispatch index

概念上：

```text
current_type_id
→ relevant patterns
→ compatible non-drop geometries
→ attack-eligible capture patterns
```

可以在 SemanticEngine 私有层建立 immutable index。

要求：

- 由 compiled IR 纯派生；
- 不改变 serialized IR；
- 不改变 ruleset fingerprint；
- no debug-name matching；
- no Shogi-specific hardcode；
- deterministic ordering 与 IR order 完全一致。

必须特别注意 `semantic_engine_for(compiled)` 当前可能创建新的 `SemanticEngine`。
如果构建 dispatch index 的成本本身 material：必须测量；不得通过危险 global mutable cache 解决；如采用 caching，必须证明 lifecycle、thread safety、identity、memory ownership。

## Option C — fixed-target attack pruning

如果 profile 证明：

```text
geometry_candidates(...)
→ 大量生成无关 target
→ 只有 target == square 才继续
```

是主要成本，可以实现 generic target-directed geometry reachability / path query。

但这是高风险选项，必须：

- 所有 geometry kind parity；
- ray/leaper/owner-relative/path exactness；
- blockers/path predicates 不得混淆；
- pseudo-attack S0/S1 semantics 不变；
- 不允许用 Shogi movement special cases。

如果不能非常严格证明，不做。

---

# 10. 明确禁止的优化

本轮禁止：

```text
attack result memoization across arbitrary positions
global mutable semantic cache
unsafe hash-only cache key
Shogi-specific attack table
bitboard rewrite
Native migration
C/C++/Rust rewrite
incremental attack map
incremental legal move cache
S3 bypass
king-safety approximation
pseudo-legal shortcut that changes semantics
remove S4 attack contribution
change action order
change evaluator
change ordering
change qsearch policy
change TT
LMR/null move/new search algorithm
parallel search
multithreading
```

GenericChess 不能建立未经声明的 Chess/Shogi 特例前提。

---

# 11. Attack semantics correctness gate

任何 optimization 前，建立 attack differential suite。

对于 baseline 与 candidate implementation：

对 deterministic corpus 中大量：

```text
position × square × by_owner
```

必须：

```text
is_square_attacked exact equal
```

至少：

- 所有 81 squares；
- both owners；
- F5 semantic prefixes；
- curated S4/promotion/drop/blocker fixtures。

对每个正式 Semantic Shogi prefix：

```text
for square in all board squares:
    for owner in (0, 1):
        before == after
```

如果能合理承受，再加入 deterministic random reachable corpus，例如 `>= 100 reachable positions` × all squares × both owners，但不要产生数小时 runner。

---

# 12. Legal-action / S3 parity gate

必须 exact parity：

```text
tuple(iter_legal_actions(position))
```

包括 **order**。

同时验证：

```text
has_legal_action
no_legal_reply / _exists_s3_reply
S3 accepted/rejected candidate set
```

必须覆盖：

```text
own_anchor_safe
squares_not_attacked
promotion
forced promotion
drop
nifu
uchifuzume
ordinary repetition
continuous_check_loss
```

Standard Shogi cshogi certified regression 继续通过。

---

# 13. Transition / terminal / history 不得漂移

F5 不以 transition 为优化目标，但任何 candidate dispatch rewrite 都必须证明：

```text
chosen public action identity exact
child normalized position exact
side-to-move exact
hands exact
promotion exact
aux exact
terminal exact
history witness exact
```

以及：

```text
F3 TT on/off parity
continuous_check parity
opaque-history TT skip
```

不得因为 candidate order / binding identity 改变影响后续 search。

---

# 14. Performance gate

只有 correctness 全绿后才允许性能判断。

对每个 semantic case：

```text
1 warm-up
5 measured repetitions
```

沿用 F4。

### Profile A

```text
TT on
ordering off
qdepth 0
root tactical off
max_depth 2
max_nodes 512
no wall-clock search limit
```

### Profile B

```text
current product/default tuning
TT on
max_nodes 256
deterministic fixed-node
```

不要用 wall-clock search limit。

报告：

```text
median
p90
min
max
nodes/qnodes
completed depth
attack counters
S3 counters
```

---

# 15. Optimization acceptance threshold

要得到：

```text
F5_RESULT = OPTIMIZATION_PASS
```

必须全部满足。

## Correctness

```text
attack differential exact
legal action set/order exact
transition exact
terminal/repetition exact
search action exact
search score exact
PV exact
nodes/qnodes exact
completed depth exact
termination exact
F3 TT regressions PASS
Round4 certified Shogi regressions PASS
```

## Performance

Semantic aggregate：

```text
Profile A median wall improvement >= 15%
```

并且：

```text
至少 3/4 Semantic Shogi Profile A cases 改善 >= 10%
```

同时：

```text
任何 Semantic Profile A case不得稳定 regression > 10%
```

Profile B：

```text
aggregate median 不得 regression > 5%
```

如果 Profile B 也明显改善，记录；不是硬要求 >=15%。

如果只有 microbenchmark 快很多但 whole search < 15%：

```text
OPTIMIZATION_GATE = FAIL_MATERIALITY
```

回滚 production optimization，保留 audit evidence：

```text
F5_RESULT = AUDIT_ONLY_PASS
```

---

# 16. Optimization commit provenance

流程必须：

```text
363c74...  baseline
   ↓
H5A        harness/tests only
   ↓
baseline measurements
   ↓
H5B        ONE optimization family
   ↓
after measurements + parity
   ↓
E5         evidence/docs only
```

要求：

- H5B parent = H5A；
- H5B 不包含 after-outcome evidence；
- 如 optimization gate FAIL：revert optimization cleanly；final production source 等价 H5A；evidence 可以记录 rejected experiment；
- 不 force push。

---

# 17. Required tests

至少运行：

```text
new F5 attack differential tests
new F5 S3 parity tests

tests/test_f3_corrective_r1.py
tests/test_search_path_runtime.py

Round 4 certified semantic Shogi regressions
interruptibility / cancellation tests
semantic stress differential
native readiness sanity
```

最后：

```text
full pytest
fresh supported Zig build
```

如果 full pytest 有既有 flaky test：fresh rerun；明确证明 baseline 同样 flake；不允许无解释 PASS。

---

# 18. Runtime safety

F4 已经出现 Profile B cProfile 60s safety abort。

F5 不允许再出现无人监管数小时 profiling。

所有 profiling subprocess：

```text
hard controller timeout <= 60 s per cProfile case
```

普通 five-run fixed-node performance：

```text
单 case controller hard timeout <= 180 s
```

如果超过：

```text
RUNTIME_SAFETY_ABORT
```

保存 partial diagnostics，继续其他 bounded case 或按 hard gate STOP。

禁止任何单个 runner 再运行 189 分钟。

---

# 19. Evidence

新增：

```text
artifacts/f5_semantic_attack_s3/
```

至少：

```text
baseline.json
corpus.json
attack_micro_baseline.json
s3_micro_baseline.json

profile_a_before.jsonl
profile_b_before.jsonl

deep_profile_before_cumulative.txt
deep_profile_before_self.txt

hotspot_analysis.json
optimization_gate.json

attack_differential.json
legal_order_parity.json
search_parity.json

profile_a_after.jsonl
profile_b_after.jsonl
performance_comparison.json

final_verdict.json
manifest.json
```

如果没有 optimization，则 after/performance 文件可以明确标记 not executed，而不是伪造。

Docs：

```text
docs/architecture/F5_EVIDENCE.md
```

如果形成值得冻结的架构决策，再新增 ADR-023；不要为了每轮都有 ADR 强行创建。

---

# 20. AlphaSho

F5 不需要 AlphaSho。

如果任何脚本读取 AlphaSho fixture：

- read-only；
- capture before/after repo state；
- exact equal。

更推荐完全不依赖 AlphaSho。

---

# 21. Final verdict

成功优化：

```text
F5_RESULT = OPTIMIZATION_PASS
SEMANTIC_ATTACK_PARITY = PASS
S3_LEGALITY_PARITY = PASS
STANDARD_SHOGI_CERTIFICATION_REGRESSION = PASS
SEARCH_PARITY = PASS
PERFORMANCE_GATE = PASS
FULL_PYTEST = PASS
NATIVE_BUILD = PASS
```

只有 audit 没有足够优化：

```text
F5_RESULT = AUDIT_ONLY_PASS
reason = ...
production_optimization_committed = false
```

正确性失败：

```text
F5_RESULT = BLOCKED
reason = ...
```

不得把 correctness failure 解释为性能 tradeoff。

---

# 22. 最终回执格式

一次性回复：

## 1. Status
- `OPTIMIZATION_PASS` / `AUDIT_ONLY_PASS` / `BLOCKED`

## 2. Baseline
- starting SHA
- H5A
- H5B if any
- master/chat states

## 3. Baseline attack/S3 audit
- attack query counters
- S3 counters
- repeated-work diagnosis

## 4. Candidate
- chosen optimization family
- why other options rejected

## 5. Architecture
- changed files
- ordering preservation
- cache/index lifecycle
- Core/Search boundary

## 6. Attack parity
- positions
- square-owner query count
- mismatches

## 7. S3/legal parity
- action set
- action order
- S3 acceptance
- S4/no_legal_reply
- Shogi special rules

## 8. Search parity
- action
- score
- PV
- nodes/qnodes/depth
- terminal/history

## 9. Performance
For each semantic case/profile:
- before median/p90
- after median/p90
- delta %
- attack/S3 work counters

## 10. Tests
- focused
- F3
- Round4
- interruptibility
- semantic/native
- full pytest
- Zig build

## 11. Evidence
- artifact tree
- manifest hash verification

## 12. Git
- H5A
- H5B
- E5
- origin/sandbox
- master/chat unchanged
- clean status

## 13. Final recommendation
Only one next phase.

---

# 23. STOP RULE

如果：

- baseline moved；
- certified fingerprint changed；
- attack parity mismatch；
- legal action order mismatch；
- search parity mismatch；
- history/TT regression；
- interactive deadline/cancellation regression；

则：

```text
preserve diagnostics
do not rationalize
do not widen scope
STOP
```

如果 F5 closure 完成：

```text
STOP
```

不要自动开始：

```text
F6
Native migration
transition cache
qsearch redesign
evaluator/search-strength tuning
```
