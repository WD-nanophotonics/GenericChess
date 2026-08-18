# GenericChess：Native Semantic Runtime Closure + Search-Ready AlphaBeta 大关卡

## 0. 任务性质

这是一个连续的大型工程任务。允许你在 `sandbox` 中自主设计、实现、重构、调试、提交和 push，不需要逐步等待 Chat 批准。

但必须遵守一个分层门槛：

> **先证明 Native semantic runtime 与 Python SemanticEngine 在多步语义上等价，再进入 semantic search。**

不要为了“赶进度”让 search 建在未经证明的状态模型上。

本任务允许并鼓励你一口气完成多个连续 checkpoint。每到一个真正稳定的里程碑就 push `origin/sandbox`，让 Chat 可以并行审计；你不需要因此停工。

---

# 1. 已冻结事实与 baseline

正式 master：

`3629c52b8c0bb4e92bd55851f2fc970d0407dadc`

已通过 Chat SHA-bound 审计的 Native semantic payload ABI checkpoint：

`38c554afb074aed391b23e356f36dc52e3d8a920`

该 checkpoint 已确认：

- setuptools native source closure 包含 `native_semantic_rules.c`；
- `GCSemInvariant.refs_count` 内存安全问题已修复；
- semantic payload v2 由 C capsule 稳定拥有 `type_ids`；
- duplicate type IDs fail closed；
- embedded NUL fail closed；
- v1 payload exact round-trip 回归存在；
- `semantic_position_state == False`；
- `semantic_s0_s4_executor == False`；
- capability 没有提前虚报。

如果你的当前本地 `sandbox` 已经是 `38c554a` 的后继并包含未 push 的有效 executor 工作：

**保留并继续，不要 reset，不要为了匹配本任务文本丢弃有效工作。**

先记录实际 HEAD、dirty state、已有变化，然后继续。

---

# 2. 总目标

把当前架构：

```text
Compiled Semantic IR v2
→ deterministic payload v2
→ C-owned GCSemanticRules
```

推进到：

```text
Compiled Semantic IR v2
→ C-owned GCSemanticRules
→ Native semantic position
→ exact semantic action generation
→ S0–S4 legality
→ checked make / trusted make-unmake
→ position identity / repetition / terminal
→ recursive semantic perft
→ Python↔Native differential proof
→ fixed-depth semantic AlphaBeta
→ exact PV
→ shallow minimax differential proof
```

最终目标不是“有几个 Native API 可以运行”。

最终目标是：

> **Python SemanticEngine 与 Native Semantic Runtime 成为两个独立执行器，并通过系统 differential tests 证明多步语义一致；随后让 Native semantic runtime 真正进入一个独立的固定深度 AlphaBeta 搜索闭环。**

---

# 3. Phase A — Build / baseline / current-work audit

先做一次工程闭包确认，不要浪费时间重新审计已经冻结的架构。

至少确认：

1. 当前 sandbox HEAD / ancestry；
2. Native extension 可重复构建；
3. Zig build 正常；
4. setuptools build path 不因 semantic source 缺失而失效；
5. 当前 payload v1/v2 tests 仍绿；
6. 当前 legacy Native surface 没被 semantic work 破坏。

如果 setuptools native build 在当前 Windows/toolchain 下本身存在与本任务无关的历史环境问题，可以记录并继续，但不能把 source closure 错误误判成环境问题。

建立一个短的 reproducible build smoke，避免后续每轮 Native 变更都靠手工猜测 extension 是否加载的是最新 binary。

必须防止：

```text
改了 C
→ pytest 实际加载旧 .pyd
→ 误以为测试通过
```

测试/脚本应能确认当前 extension 是由当前 source/commit 构建。

---

# 4. Phase B — Native semantic position

建立独立于 legacy `GCPosition` 的 semantic position/state。

不要硬把 legacy position 扩成一个充满 semantic 特例的结构，除非你能证明重构后边界仍然干净。

Native semantic position 必须无损表达 Python SemanticEngine 所需的完整动态状态，至少包括：

- board occupancy；
- piece owner；
- base type identity/index；
- current type identity/index；
- promoted state；
- hands / capture-to-hand 所需 base type counts；
- side to move；
- ply；
- semantic aux slots：
  - bool；
  - square_or_none；
  - global / per_owner；
  - lifetime；
- repetition identity/history 所需状态；
- terminal/max-ply/repetition 判断所需信息。

不得丢失：

```text
base/current/promoted
```

的区别。

不能因为两个 position 的当前棋盘看起来相同，就在：

```text
hand base identity
aux state
promotion identity
history/repetition context
```

不同的情况下认为它们相同。

---

# 5. Native position public boundary

提供尽可能小但足够测试的 Python-facing API。

建议能力而非强制函数名：

```text
semantic_pack_position(...)
semantic_position_info(...)
semantic_position_key(...)
semantic_legal_actions(...)
semantic_make_checked(...)
semantic_child_snapshot(...)
semantic_terminal(...)
semantic_perft(...)
```

API 名称可调整，但必须能从 Python：

1. 将一个 Python semantic position 打包成 Native；
2. 读取 Native 完整 canonical snapshot；
3. 获取 legal exact packed actions；
4. checked apply 一个 exact action；
5. 获取 child snapshot；
6. 做 recursive perft。

不要要求 Python 在 Native 每一个 node 上参与执行。

Python 只允许：

- pack 初始测试数据；
- 调 Native public API；
- 作为 differential oracle。

禁止：

```text
Native executor
→ callback Python SemanticEngine
→ 得到 legal actions / child
```

这种假 Native。

---

# 6. Phase C — Position identity / SHA-256 / repetition

这是本轮必须认真解决的部分。

Python semantic runtime 当前的 position identity 是权威。

Native 必须建立与 Python authority 对齐的 canonical semantic position identity。

如果 Python authority 使用 canonical JSON + SHA-256：

- Native 必须产生相同 canonical bytes / digest；
- 不得使用平台相关 struct bytes；
- 不得依赖指针值；
- 不得使用 Python hash；
- 不得使用 locale；
- 不得使用不稳定 map iteration；
- string/type identity 必须对应 payload v2 stable `type_ids`。

如果你发现 Python position-key authority 的 canonicalization 事实上并不是适合 C 机械复现的形式：

- 不要偷偷定义第二套 identity；
- 找出最小 authority refactor；
- 保持 Python 和 Native 共用同一个冻结的 canonical contract；
- 用 regression 锁死。

需要覆盖：

```text
board
hands
side
aux
base/current/promoted
```

以及 Python authority 中真正属于 position identity 的字段。

同时明确区分：

```text
position identity
vs
search-context identity / repetition history
```

如果 repetition legality 或 TT correctness 依赖历史上下文，不允许错误地把“当前位置 digest”当成“全部历史上下文”。

实现 C 侧 SHA-256 时：

- 可以采用项目内小型自包含实现；
- 或使用已经稳定可用的标准/平台实现；
- 不要引入巨大依赖只为了 SHA-256；
- 加 known-answer tests。

至少验证：

```text
SHA256("")
SHA256("abc")
```

以及 Python↔Native semantic position key parity。

---

# 7. Phase D — Exact semantic action identity

ADR-017 的 64-bit exact semantic action identity 是冻结边界。

Native legal action generation 必须保留：

- action family / kind；
- pattern identity；
- geometry identity；
- actor base type；
- actor current type；
- source；
- target；
- promotion identity；
- drop identity；
- layout 中已有的其他冻结字段。

禁止：

```text
first matching pattern
coordinate-only action identity
source+target fallback
reconstruct action by guessing pattern
```

必须建立 action pack/unpack regression，特别覆盖：

- 同 source/target 但 pattern 不同；
- 同 source/target 但 geometry 不同；
- promotion choice collision；
- drop identity；
- base/current identity collision。

Native legal set 与 Python oracle 比较时：

> 比 exact packed identity set，而不是只比坐标。

---

# 8. Phase E — S0–S4 Native legality executor

实现 Python `SemanticEngine` 当前支持语义的 Native 等价执行。

必须覆盖：

## Candidate / actor / geometry

- board actions；
- drops；
- exact pattern binding；
- geometry path；
- owner-relative geometry；
- actor base/current binding。

## Target / path predicates

- target_empty；
- target_enemy；
- target_friendly；
- target_any；
- path_clear；
- path_count_eq；
- path_count_range；
- path_first_blocker_owner；
- path_last_blocker_owner。

## State guards

- aggregation exists/count；
- owner self/opponent/any；
- base/current compare field；
- promoted yes/no/any；
- type refs；
- spatial selectors：
  - same_file；
  - same_rank；
  - exact；
  - adjacent；
  - path_between；
  - zone。

## Slot guards

- bool；
- square_or_none；
- eq/ne；
- 现有 IR 支持的其他合法 comparison 组合。

## Effects

- move；
- shift；
- remove；
- capture_to_hand；
- remove_from_game；
- remove_from_hand；
- place；
- set_current_type；
- set_bool；
- clear_right；
- set_token；
- clear_token。

必须遵守 effect ordering。

## Promotion

- none；
- inherit_compiled_masks；
- explicit；
- optional/forced promotion；
- alive promotion targets；
- drop 后不能无依据立即 promotion；
- capture 回 hand 的 base identity。

## Aux lifetime / triggers

- persistent；
- expire_next_turn；
- global/per_owner；
- piece_leaves_square；
- piece_removed_from_square。

必须确认 trigger 观察的是 Python authority 所定义的“事件语义”，而不是简单从最终 board diff 猜。

## Invariants / attack

- pseudo-attack；
- own_anchor_safe；
- squares_not_attacked；
- transit square attack 等 castling 类约束。

## Postconditions / S4

- opponent_checked；
- no_legal_reply；
- bounded probe；
- max_stratum 必须严格执行；
- 禁止 S4 probe 递归失控。

Uchifuzume 是本阶段硬验收。

---

# 9. Attack / check 必须与 legality 分层

不要用“完整 legal move generation”代替 pseudo-attack。

明确建立：

```text
pseudo attack
check detection
legal action
postcondition reply probe
```

之间的层次。

避免产生：

```text
is_attacked
→ legal_actions
→ invariants
→ is_attacked
```

无限递归。

对于 `squares_not_attacked`、own-anchor safety 等必须和 Python SemanticEngine 的定义一致。

---

# 10. Phase F — Checked make / trusted make-unmake

提供两个层次：

## Public checked apply

收到任意 packed action：

1. 解包；
2. 验证字段/domain；
3. 验证 exact action 当前确实 legal；
4. 失败时 position **完全不变**；
5. 成功后得到正确 child。

错误必须 fail closed。

## Trusted recursive make/unmake

供 perft / search hot path 使用。

Undo 必须恢复所有动态字段：

- board；
- owner/base/current/promoted；
- hands；
- side；
- ply；
- aux；
- aux lifetime state；
- repetition/history bookkeeping；
- position digest/hash cache；
- terminal bookkeeping；
- 任何新增 runtime cache。

做强 regression：

```text
snapshot_before
make
unmake
snapshot_after
assert exact_equal
```

不仅比 board。

针对每类复杂语义：

- castling；
- en passant；
- token；
- clear_right；
- capture_to_hand；
- promotion；
- drop；
- trigger；
- S4 probe 内部 make/unmake；

都做 round-trip。

---

# 11. Phase G — Recursive semantic perft

必须有真正进入 C recursion 的：

```text
semantic_perft(position, depth)
```

depth=0 返回 1。

不得 Python 每层循环 legal actions 再调用 Native child。

至少支持：

```text
depth 0
depth 1
depth 2
depth 3
```

对小规则/低分支规则尽量增加 depth 4 或更深。

Perft 的意义是证明：

```text
legal generation
+
make/unmake
+
multi-ply dynamic state
```

同时工作。

---

# 12. Phase H — Differential harness

这是整个 runtime closure 的核心验收，不是附属测试。

建立固定、可重放的 Python↔Native differential harness。

固定 corpus 至少包括：

1. legacy-lowered/random simple rules；
2. Cannon；
3. Castling；
4. En Passant；
5. Nifu；
6. Uchifuzume / S4；
7. promotion optional/forced；
8. multiple promotion targets；
9. drops；
10. capture-to-hand；
11. mirrored owner-relative geometry；
12. aux bool；
13. aux square token；
14. exact action identity collision cases；
15. max-ply；
16. repetition；
17. compound move/effect order；
18. deliberately awkward/weird semantic fixtures already present in tests。

对于每个相同 position 比较：

```text
exact legal packed-action set
canonical child full state
position key
in_check
attacked-square / relevant attack queries
terminal result
```

对多步：

```text
perft node count
```

必须做 fixed-seed randomized legal playout。

建议最低：

- 每个主要 corpus 多个 seed；
- 总计至少数百个中间 position；
- 每个 position 比 exact action set；
- 随机选择合法 action 后继续多 ply；
- 每次都比较 child。

如果性能允许，增加到上千 position。

任何 differential failure 必须输出可重放信息：

```text
ruleset/fingerprint
seed
ply
canonical position
Python actions
Native actions
missing
extra
chosen action
```

不要只报：

```text
assert False
```

---

# 13. Negative / malformed position tests

不仅测试合法 position。

Native pack/public checked API 必须拒绝：

- unknown type index；
- owner 非 0/1；
- base/current 不一致；
- promoted flag 与 current type 不一致；
- anchor 非法 promoted；
- hand count overflow；
- invalid aux kind/value；
- square out of board；
- side invalid；
- max ply overflow；
- malformed packed semantic action；
- rules capsule/position fingerprint mismatch。

失败时不得留下半初始化 Native object。

---

# 14. Memory safety / stress

Native semantic runtime 会有大量 nested state + undo。

至少做：

- repeated create/free；
- repeated pack/free；
- deep make/unmake loop；
- repeated S4 reply probe；
- repeated perft；
- exception/error path cleanup。

如果当前 Zig/clang 环境方便启用 AddressSanitizer，增加一个 focused ASan smoke。

如果 Windows toolchain/extension loading 使 ASan 成本异常高，可以记录为 non-blocking；但普通测试中不能有 crash、heap corruption 或 obvious leak-growth。

---

# 15. Runtime capability gate

只有当 position state + differential tests 真正完成后：

```text
semantic_position_state = True
```

只有当 S0–S4 legal generation / make-unmake / perft parity 真正完成后：

```text
semantic_s0_s4_executor = True
```

不要因为“函数存在”就置 True。

`SemanticCapabilities.native_executable` 必须重新审视其语义。

如果它表示：

> 当前 compiled semantic ruleset 的全部必要语义可由 Native 独立执行

那么只有满足这个定义时才能 True。

对于 Native 不支持的 S5 或未来 primitive：

- fail closed；
- 不要全局虚报。

---

# 16. Runtime closure checkpoint

完成 Phase A–H 后，创建并 push 一个明确 checkpoint。

建议 commit message：

```text
Complete Native semantic runtime parity
```

或其他清晰名称。

在这个 checkpoint 上至少跑：

1. semantic payload focused suite；
2. semantic runtime focused suite；
3. differential suite；
4. legacy Native focused suite；
5. full pytest（如果时间合理）。

记录真实结果。

**Push 后不要停工等 Chat。**

只要 Phase A–H 全绿，就可以继续下面的下一阶段。

---

# 17. Phase I — 下一阶段：Semantic fixed-depth AlphaBeta

只有 Runtime Closure 全绿后进入。

目标不是立刻复制所有 legacy iterative-search 工程。

先建立最小但真正独立的：

```text
semantic_fixed_depth_search
```

要求：

- 搜索节点完全使用 Native semantic position；
- legal actions 完全使用 Native semantic executor；
- make/unmake 完全 Native；
- 不回调 Python；
- terminal 使用 semantic terminal；
- 返回 exact packed best action；
- 返回 exact packed PV；
- deterministic；
- 支持固定 depth；
- alpha-beta pruning。

先不要加入：

- iterative deepening；
- node/time budget；
- cancellation；
- aspiration；
- parallel search；
- GUI。

这些之后再说。

---

# 18. Generic semantic evaluation

Semantic AlphaBeta 不能偷用 game-name 特例。

优先复用当前 GenericChess 已有的 generic evaluation/profile 思路：

```text
board value by type
hand value by base type
promotion/material terms
```

但需要重新确认它能否安全绑定 semantic payload v2 `type_ids`。

要求：

- evaluation table 与 ruleset fingerprint/type identity 对齐；
- board 用 current type 或既有 authority 定义；
- hand 用 base type；
- terminal mate score 独立于 material；
- 不能把 legacy `GCPosition` 指针偷偷传进 semantic search。

如果现有 NativeEvaluationTables 与 legacy `GCRules` 强绑定：

> 做一个小而干净的 semantic evaluation compilation/adapter，不要为了复用而制造错误耦合。

本阶段不要求复杂 positional heuristic。

Material-only generic evaluation 足够作为 search correctness 验证。

---

# 19. AlphaBeta correctness oracle

为 semantic fixed-depth search 建一个**测试用途的 Python brute-force minimax/alpha-beta oracle**。

它可以慢，因为只用于：

- 小棋盘；
- 小分支；
- depth 1–3；
- fixed corpus。

比较：

```text
root score
best exact action
PV legality
terminal mate scores
```

如果存在多个同分 best action：

- 定义 deterministic tie-break；
- 或比较 best-score set；
- 不要因无关 action ordering 产生伪失败。

至少覆盖：

- simple legacy-like；
- Cannon；
- Castling；
- En Passant；
- Nifu；
- 一个 promotion/drop case；
- 一个 S4/uchifuzume 小局面（深度可低）。

---

# 20. PV 验证

Native 返回的 PV 必须逐步合法。

测试：

```text
root
→ PV[0]
→ child
→ PV[1]
→ ...
```

每一步 action 必须存在于该 position 的 exact legal set。

不能只返回 root move 后拼接未验证缓存。

---

# 21. TT：本轮只在 correctness 明确后做

如果 fixed-depth AlphaBeta 在无 TT 情况下已经正确，可以加入 semantic TT。

但 TT key 必须正确处理：

```text
semantic position identity
+
repetition/search context where required
```

如果同一个当前 position 在不同 repetition context 下 terminal/legal value 可能不同：

> 不能只使用裸 position SHA 作为 TT correctness key。

可以：

- 将必要 context 纳入 key；
- 或本轮先不启用 TT。

**宁可没有 TT，也不要 unsafe TT。**

如果实现 TT，增加 targeted repetition-context collision regression。

---

# 22. Search checkpoint

完成 fixed-depth semantic AlphaBeta 后 push 第二个明确 checkpoint。

建议：

```text
Add Native semantic fixed-depth search
```

这个 checkpoint 将接受 Chat 的下一轮独立 SHA-bound audit。

仍然不要 merge master。

---

# 23. 明确禁止

整个任务中禁止：

- game-name special cases：
  - chess；
  - shogi；
  - cannon；
  - en passant；
  - castling；
  - nifu；
  - uchifuzume；
- Python callback hot path；
- coordinate-only action identity；
- 用 legacy movegen 假装 semantic executor；
- 用 legacy GCPosition 假装 semantic position；
- 为通过 tests 硬编码 fixture；
- capability 虚报；
- 未证明 runtime parity 就做 search；
- 修改 master；
- force push；
- 把 `coordination/` 混入未来 master candidate。

---

# 24. 允许的工程判断

你拥有实现自由。

允许：

- 新 C 文件；
- 新 header；
- 重构 native_module binding；
- 增加 semantic runtime module；
- 自包含 SHA-256；
- SQLite/外部服务不需要；
- 增加 Python adapter；
- 增加 tests/differential harness；
- 调整 build scripts；
- 为清晰边界抽取公共 utility。

但应优先：

```text
correct
deterministic
fail-closed
auditable
```

而不是追求早期 micro-optimization。

---

# 25. Push / 并行审计策略

你不需要等 Chat 批准每个小 commit。

建议至少 push：

1. semantic position + key 基础 checkpoint；
2. S0–S4 executor + make/unmake + perft runtime-closure checkpoint；
3. fixed-depth semantic AlphaBeta checkpoint。

如果中间发现一个值得独立审计的 ABI 改动，也可以额外 push。

Chat 会并行审计已 push SHA，并通过 Gmail `[GC-BRIDGE][AUDIT]` 返回意见。

收到 FAIL：

- 修复；
- 新 SHA；
- 旧 PASS/FAIL 不转移到新 SHA。

收到 PASS：

- 继续。

---

# 26. 最终回执

完成本大关卡后报告：

## Repository

- 起点 HEAD；
- runtime closure checkpoint SHA；
- search checkpoint SHA；
- `origin/sandbox` HEAD；
- master 未改证明；
- worktree status。

## Architecture

- Native semantic position 数据布局；
- ownership；
- aux representation；
- history/repetition representation；
- canonical position key；
- SHA-256 implementation；
- action identity；
- make/unmake；
- attack/check layering；
- S4 bounded probe；
- search/eval/PV architecture。

## Public API

列出新增 Native/Python API。

## Differential

报告：

- corpus；
- seeds；
- positions compared；
- perft depths；
- action-set parity；
- child-state parity；
- key parity；
- terminal parity；
- attack/check parity；
- randomized playout parity；
- failures encountered/fixed。

## Search

报告：

- depths；
- oracle cases；
- score parity；
- best-action parity；
- PV validation；
- TT 是否实现；
- 如未实现，原因。

## Tests

报告真实：

- Zig build；
- setuptools build smoke；
- payload tests；
- runtime tests；
- differential tests；
- search tests；
- legacy focused tests；
- full pytest；
- sanitizer smoke（如运行）。

## Capabilities

明确最终：

```text
semantic_ir_v2_compile
semantic_payload_version
semantic_exact_action_identity
semantic_position_state
semantic_s0_s4_executor
native_executable
```

及每个值的理由。

---

# 27. 完成定义

如果最终只是：

```text
Native 能 pack position
Native 能出几步 legal move
几个 fixture 通过
```

不算完成。

Runtime closure 完成的定义是：

> **Native 能完全独立执行 Python SemanticEngine 当前 S0–S4 支持语义，在多步 make/unmake/perft/random playout 上与 Python oracle 精确一致。**

整个大关卡完成的定义是：

> **在上述独立 semantic runtime 上，Native fixed-depth AlphaBeta 能返回正确 score / exact best action / exact legal PV，并通过小规模 Python minimax differential verification。**

做到这里再停止，不继续做 iterative deepening/time/cancel/UI/online。
