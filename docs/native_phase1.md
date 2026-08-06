# GenericChess Native Phase 1 — Rule Kernel & Perft Backend

状态：**experimental（0.7.0a1）**。本阶段实现一个可由 Python 调用的 native rule kernel
（C17 + CPython C API），并以 Python Core 为 oracle 完成 legal-move / perft differential
validation。尚未实现 native AlphaBeta（那是 Native Phase 2）。

## 1. 构建

开发机（Windows x64，无 Visual Studio C++ 工具链）使用 Zig 自带的 clang 编译：

```powershell
.\.venv\Scripts\python.exe -m pip install ziglang   # 一次性
.\.venv\Scripts\python.exe scripts\build_native_zig.py
```

产物：`generic_chess/_native_core.cp313-win_amd64.pyd`（gitignore，不提交）。
`pyproject.toml` 同时声明了 `optional=True` 的 ext-module，MSVC 环境可直接
`pip install -e .` 构建。未构建时 `generic_chess.native.native_available()` 返回 False，
原生测试自动 skip，Python Core 仍可完整使用。

## 2. Native ABI（冻结约定）

* Square：`index = rank * width + file`（rank 0 为第一行），与 Python Core 线性化一致。
* Type：0..type_count-1，按 type_id 字典序映射；adapter 持有双向映射。
* Piece：`{base_type, current_type, owner, promoted, occupied}`（首版不 bit-pack）。
* Packed action（64-bit）：bits 0-7 to；8-15 from（drop 为 0xFF）；16-23 promotion target
  （0xFF=无）；24-31 base type；32-35 kind（0=board，1=drop）。mask/shift 集中定义于
  `native_types.h`。
* Board：`GCPiece board[GC_MAX_SQUARES]`（≤16×16）。Hand：`uint16_t hand[2][type_count]`。
* Undo：`GCUndo` 恢复 board / side / ply / hands / history_len / hash。
* Hash：128-bit（lo/hi）确定性 Zobrist，表由 fingerprint 经 splitmix64 派生（无系统随机）；
  piece 按 (owner,square,current_type,promoted)，hand 按 (owner,type,slot) 逐件增量；
  make/unmake 增量更新，debug 可全量重算校验。
* Repetition：`history[]` 栈 + root_hash_count（来自 Python repetition_counts 的当前 key
  计数），与 Core 的 4 次重复语义一致。

## 3. 规则编译

`compile_native_rules(compiled)` 一次性把 RuleSet 编译为 native 表：type map、atoms
（leap/ray + owner-relative 方向）、promotion targets、promotion allowed pairs、forced
to-squares、alive-promotion mask（结构性死亡 target 过滤）、drop mask、anchor 标记、
repetition/max-ply 配置、Zobrist 表。不支持的规则（board>16、type>64、atom>16、target>8）
抛 `NativeUnsupportedRuleError`（含 fingerprint、type、schema version），绝不静默降级。

## 4. Native 语义

* leap：越界/友方/敌方 anchor 处理与 Python 一致；ray：依序、首个占据格停止（占据格本身
  被攻击但不可捕获）；promotion expansion 使用编译 mask（非按 last-rank 重推）；drop 按
  mask + hand + 空格。
* legality：pseudo → make → 己方 anchor 是否被攻 → unmake；与 Python `_is_legal` 一致。
* attack：`gc_is_square_attacked` 与 Python `pseudo_attacks` 一致（pinned 仍攻击、ray 遮挡、
  leap 无遮挡、敌方 anchor 被攻击不可捕获）。
* terminal：moves 空 → checkmate/stalemate（优先于 repetition/max-ply）；否则 repetition；
  否则 max-ply —— 与 Core `_terminal_from_parts` 顺序一致。
* perft：depth 0 → 1；terminal 节点在 depth>0 贡献 0 —— 与 correctness corpus 定义一致。

## 5. Differential evidence

* correctness corpus（12 fixtures）：legal action canonical set 与 perft depth 1-3 全部一致。
* targeted fixtures（6 类）：legal set、make/unmake roundtrip、perft depth 1-2 全部一致。
* deterministic fuzz：多规则集 × 多局面 legal set 一致。
* attack maps：精选 fixture 逐格一致。
* make/unmake：hash_after_make/hash_restored/state_restored 全部通过。
* 诊断：`python -m generic_chess.native.differential [--fixture ID] [--show-actions]
  [--show-attack-map] [--perft-depth N]`。

## 6. 性能（本机，2026-08-06）

| fixture | size | depth | nodes | python wall (s) | native wall (s) | speedup | native NPS |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| gen_classic_like_4_101:opening | 4 | 3 | 126 | 0.018 | 0.0002 | 95× | 0.9M |
| gen_classic_like_6_201:opening | 6 | 3 | 6321 | 1.423 | 0.002 | 717× | 3.2M |
| gen_classic_like_8_301:opening | 8 | 2 | 2727 | 1.660 | 0.002 | 956× | 1.6M |
| gen_ray_heavy:opening | 8 | 2 | 7677 | 5.928 | 0.013 | 466× | 0.6M |
| gen_leap_heavy:opening | 8 | 2 | 256 | 0.074 | 0.0003 | 235× | 1.0M |
| hb_forced_promo:opening | 6 | 3 | 104 | 0.016 | 0.0001 | 147× | 1.4M |
| hb_multi_promo:opening | 6 | 3 | 167 | 0.026 | 0.0001 | 191× | 1.6M |

说明：Python perft 参考实现每个 child 都做完整 legal_successors + SHA-256 position key +
terminal 检测，是刻意保守的 oracle；speedup 是相对该 oracle 的数值。native perft 全递归
在 C 内，FFI 只在根调用一次。

## 7. 已知限制

* 尚无 native AlphaBeta/qsearch/TT/evaluator（Phase 2）。
* native hash 是搜索态 hash，不是正式存档 key（Python `position_key` 保持唯一权威）。
* 首版 movegen 从编译 atoms 即时计算（未预计算全目标表）；perft 用 plain make（hash 正确性
  由差分测试覆盖）。
* repetition 的过去历史仅能由 root_hash_count 部分携带（无法重建任意旧局面的 native hash），
  差分测试覆盖的是 corpus/targeted/fuzz 中的实际场景。
* 构建依赖 Zig（本机）或 MSVC（可选）；未构建时 native 测试 skip。

## 8. 下一阶段（Native Phase 2）

将 AlphaBeta/PVS/TT/qsearch/evaluator 热循环移入完整 NativeSearchBackend：Python 每次思考
只跨边界一次，native 内部持有 state/make-unmake/movegen/hash/TT/搜索递归；以本阶段 perft
kernel 为地基，继续以 Python Core 做 differential oracle。
