# GenericChess：Native Generic Semantics 审计与实施任务

审计日期：2026-08-09  
审计事实源：`WD-nanophotonics/GenericChess` 当前远端 `master`  
审计基线：`3629c52b8c0bb4e92bd55851f2fc970d0407dadc`（与 `master` identical）  
项目版本：`0.8.0a9`；Native 版本：`0.4.0`

## 一、审计结论

当前链路不是“四层均已完成”，而是前三层完成、第四层尚未开始执行：

```text
RuleSet / Semantic DSL
  → Compiled Semantic IR v2                 已完成
  → Python SemanticEngine（S0–S4 oracle）   已完成
  → deterministic native payload
      → C-owned GCSemanticRules capsule      已完成
  → Native semantic state / executor         缺失
```

因此，当前真正需要完成的技术任务非常明确：让 C 端首次能够只依赖 `GCSemanticRules + native semantic position + packed semantic action`，独立生成并执行与 Python `SemanticEngine` 一致的 generic semantics。

### 1. Semantic IR

`generic_chess/rules/ir.py` 已经提供可执行闭包：

- `CompiledGeometry` 保存逐 owner、逐 source 的确定有序路径，执行器无需重新解释方向或 `max_steps`；
- pattern 完整包含 target/path/state guard/slot guard/effects/invariants/postconditions/promotion/composition 后的规范化结果；
- aux slot、transition trigger、zone、type/square ref 都已编译；
- `validate_ir` 与 `validate_executable_completeness` 执行 fail-closed 完整性校验；
- IR 版本固定为 v2。

这里已经具备 Native 执行所需的信息，不需要重新设计 DSL，也不应在 C 中读取高层 `RuleSet` 或重新推导规则。

一个需要顺手澄清的小问题是：`SemanticCapabilities.native_executable` 的含义目前不完全一致。`lower_legacy_to_ir()` 给 legacy lowering 标为 `True`，而真正的 semantic ruleset 编译结果为 `False`。在 Native semantic executor 完成后，应让该能力位表达清楚且可测试，避免把“legacy Native 可执行”与“当前 IR 可由 semantic Native executor 执行”混为一谈。

### 2. Python reference executor

`generic_chess/core/semantic_executor.py` 的 `SemanticEngine` 已经覆盖：

- exact pattern / geometry / actor binding；
- board move 与 drop candidate；
- target、path、state guard、slot guard；
- promotion；
- compound effects、hand、off-target remove/place、aux effects；
- aux expiration 与 transition triggers；
- pseudo-attack、own-anchor safety、`squares_not_attacked`；
- S4 `opponent_checked + no_legal_reply` bounded probe；
- terminal / repetition / max-ply；
- lossless public `SemanticBoardMove` / `SemanticDropMove` identity。

它可以作为差分 oracle。Native 不需要、也不允许发明另一套规则解释。

文件顶部仍残留“Python S0-S3”“S4 fail-closed”等旧阶段文字，与当前实现不符；实现任务中可一并修正，但这不是架构问题。

### 3. Native payload / compilation

`generic_chess/native/compiler.py` 与 `generic_chess/_native/native_semantic_rules.{h,c}` 已经完成：

- deterministic numeric lowering；
- type / pattern / geometry / zone 的稳定索引；
- support 与 IR runtime fields 的静态闭包；
- C-owned `GCSemanticRules`；
- payload → capsule → reconstructed payload 精确 round-trip；
- semantic packed action 的 64-bit identity layout；
- structural validation 与大小上限 fail-closed。

当前 CPython surface 只有：

- `compile_semantic_rules`
- `semantic_rules_info`
- `semantic_action_layout`

这里没有 position 或 executor API。

另有一个真实构建缺口：`pyproject.toml` 的 setuptools C source 列表没有包含 `generic_chess/_native/native_semantic_rules.c`。Zig 脚本可能通过 glob 构建成功，但标准 setuptools 构建路径并未随 C-1 同步，实施时应修复并验证两条构建路径中项目实际承诺支持的路径。

### 4. Native executor

Native 能力位当前明确报告：

```text
semantic_ir_v2_compile         = True
semantic_exact_action_identity = True
semantic_position_state        = False
semantic_s0_s4_executor        = False
```

现有 `GCPosition / GCUndo / native_movegen / native_search` 全部是 legacy `GCRules` 路径：

- `GCPosition` 没有 semantic aux state；
- `GCUndo` 只能描述普通 source/target capture/drop/promotion；
- legacy movegen 不理解 pattern、geometry、guards、compound effects、triggers 或 S4；
- legacy checked make 主动拒绝 semantic action kind 2/3；
- `GCSearchContext` 硬绑定 `GCRules` 与 legacy movegen/make/unmake。

所以不能通过给旧 movegen 加几个条件就完成。Agent 可以自行选择独立 semantic state/executor，或提取可共享的底层设施；关键验收条件是语义独立、无 Python 热路径回调、可递归 make/unmake，并与 Python oracle 差分一致。

## 二、交给工程 Agent 的实施任务

下面整段可以直接交给 Agent。

---

你现在在 `WD-nanophotonics/GenericChess` 工作。新协作工作流只保留 `master / sandbox / chat` 三个 worktree：`master` 是正式产品线，`sandbox` 是你的主要工程开发区，`chat` 保存计划、提示词、审计与 artifacts。请在 `sandbox` 中完成实现；不要恢复旧 SOL/LUNA/三角色、workflow guard、角色绑定、旧 C-2 分支治理或旧分支权限规则。

当前唯一基线是远端 `master`：

```text
3629c52b8c0bb4e92bd55851f2fc970d0407dadc
```

开始前确认你的代码树确实基于这个提交，并先运行可用的 baseline 测试。不要把旧 stash、旧 implementation branch 或旧 C-2 文档当作实现来源。

### 目标

实现第一套真正执行 GenericChess Semantic IR v2 的 Native runtime，并形成一个可以从 Python 公共入口端到端验证的闭环：

```text
CompiledSemanticRuleset
→ C-owned GCSemanticRules
→ native semantic position
→ native S0–S4 legal actions
→ exact packed semantic actions
→ native make/unmake
→ recursive perft / multi-ply execution
→ 与 Python SemanticEngine 差分一致
```

完成后，Native 必须在生成和执行每一个语义动作时只依赖编译后的 semantic payload 与 native position。搜索热路径中不得调用 Python callback，不得读取高层 `RuleSet`、`movement_atoms`、game/fixture 名称，也不得借 `_legacy_compiled` 解释语义。

### 必须交付的能力

1. Native semantic position 能无损表示 Python semantic position 的 board、hand、side、ply、aux state，以及完成 terminal/repetition 所需的身份与历史信息。
2. Native legal-action executor 完整覆盖当前 Python `SemanticEngine` 已支持的 S0–S4：geometry、target/path predicates、state/slot guards、promotion、effects、aux lifecycle、triggers、pseudo-attack、invariants，以及 bounded `no_legal_reply` probe。
3. Native 生成的动作使用 ADR-017 已冻结的 exact 64-bit semantic action identity；Python ↔ packed action 往返必须保留 pattern、geometry、actor base/current、source/target、promotion/drop identity，禁止 first-match 或坐标歧义降级。
4. 提供 checked public execution，以及供递归执行使用的 trusted make/unmake。任意失败不得留下部分修改后的 position；make→unmake 必须逐字段恢复。
5. 提供至少一个真正递归的 Native semantic entry point（推荐 semantic perft），证明多 ply 中 legal generation、make/unmake、aux、hash/history 都在 C 内闭环执行，而不只是单步把 Python 结果搬进 C。
6. 为 Python 层提供清晰、最小而可用的 wrapper/API，使测试可以编译 semantic rules、打包 position、取得 Native legal actions、checked apply，并运行递归验证。API 名称和文件组织由你根据现有项目风格决定。
7. 完成后才把 `semantic_position_state` 与 `semantic_s0_s4_executor` capability 置为 `True`；同时整理 `CompiledSemanticIR.capabilities.native_executable` 的含义，使成功编译且受支持的 semantic ruleset 能得到一致、可测试的能力声明。仍不支持的输入必须 fail closed。
8. 保持现有 legacy Native compile/movegen/make/perft/search 行为兼容。允许提取共享底层设施，但不得用 semantic 改造破坏 legacy 路径。
9. 修复本审计发现的构建闭包问题：标准扩展构建配置必须包含 semantic C sources；验证项目实际支持的 Native 构建方式。

### 正确性验证

不要只写若干手工 happy-path 测试。建立可维护的 Python-vs-Native differential harness，至少覆盖现有 semantic fixtures/corpus：

- legacy-lowered 普通随机规则；
- cannon path predicates；
- castling compound move、rights、attacked transit squares；
- en passant token、过期、off-target capture；
- nifu state guard；
- uchifuzume / S4 bounded reply probe；
- promotion、drop、capture-to-hand、两方镜像；
- action identity 冲突场景；
- make/unmake、aux state、position identity/hash/history；
- 多 ply perft counts。

对同一 position，至少比较：

```text
legal action exact identity set
child position full state
in_check / attacked-square results
terminal result
multi-ply node counts
```

增加固定 seed 的随机合法 playout / make-unmake differential；失败时输出足以重放的规则 fingerprint、position、action 与 seed。不要依赖无限随机压力测试代替确定性回归。

### 实施边界

本任务的闭环终点是“Native semantic executor 可独立、递归、差分正确地执行当前 IR”。不要求在同一任务中改 UI、Learner、online play 或产品交互。

现有 AlphaBeta/search 接入不是本任务的硬验收项，因为当前 `GCSearchContext`、evaluation 与 TT 都硬绑定 legacy structures。你可以为未来接入留下清晰接口或提取必要的共享抽象，但不要为了声称“接入搜索”而复用错误的 legacy state，或在搜索节点回调 Python。完成 executor 闭环后停止，让下一阶段基于真实 runtime 再接 search/eval/TT。

除上述语义权威、兼容性和验收结果外，不冻结内部结构名、文件列表、提交拆分或实现顺序。你有权根据代码现状重构相关 Native/Python glue；如果发现 payload 缺少执行所需字段，应以 Python IR/support 为权威，补齐 payload 与 round-trip tests，而不是在 C 中猜测。

### 完成标准与回执

完成前运行：

- 新增的 focused semantic Native tests；
- 现有 semantic Python tests；
- 现有 legacy Native correctness/perft/search tests；
- full pytest suite；
- Native build smoke test。

最终回执请简洁报告：

1. 起点与最终 commit；
2. 实际架构和公共 API；
3. Native 已覆盖的 semantic strata/primitives；
4. differential corpus、随机 seed/规模与测试结果；
5. legacy 回归结果与 full-suite 结果；
6. capability/version/build 变化；
7. 尚未进入的 search/eval/TT 接入点；
8. `git status` 与工作树状态。

如果发现当前 IR/payload 在原则上不足以无歧义执行某一已被 Python 支持的 primitive，请停止在那个具体问题上，给出最小复现和所缺信息；不要偷偷回读高层 RuleSet，也不要用 fixture 名称或规则特例绕过。

---

## 三、阶段定位

这个任务完成后，项目才真正到达：

> Semantic IR v2 在 Python 与 Native 中具有两个独立执行器，并由差分测试证明二者语义一致。

届时下一阶段才适合把 semantic runtime 接入现有 Native AlphaBeta/search/evaluation/TT；那一步将是“搜索消费 generic semantics”，而不是继续补执行语义本身。
