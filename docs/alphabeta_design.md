# GenericChess 0.4.0：通用 AlphaBeta Heuristic Player 设计说明

## 目标与原则

`generic_chess.ai` 是一个适用于任意 GenericChess RuleSet 的通用 AlphaBeta 玩家。它不依赖
任何传统棋种的名称、固定子力表、开局知识或人工棋理：棋子价值完全由 RuleSet 自身的 movement
geometry（LEAP/RAY、遮挡、边界）、升变关系、drop mask、anchor/royal 语义与终局规则自动推导。
同一个几何规则即使换用完全不同的随机 `type_id`，其基础能力估值也相同。

搜索正确性优先：v0.4 不加入 null-move、LMR、futility、razoring、singular extension、
多线程等高级剪枝。先建立“reference minimax == alpha-beta == alpha-beta + TT”的正确性基线。

## 棋子价值模型

### mobility-density 曲线

核心量是占据密度下的期望行动力 `m(ρ) = E[|L_t(x; O_ρ)|]`。默认密度点
`(0.0, 0.125, 0.25, 0.375, 0.5)`，默认一半友方一半敌方占据。

纯 LEAP / RAY 类型使用解析期望（无 Monte Carlo）：

* leap：单目标期望贡献 `1 - ρ_f`，`m = k·(1-ρ_f)`；
* ray：第 j 步可计入需前 j-1 格全空且第 j 格非友方，期望
  `Σ (1-ρ)^{j-1}·(1-ρ_f)`。

因此空棋盘时 ray 与 leap 可以相同，密度升高后 ray 衰减更快，leap 对中间阻挡不敏感。
混合/重叠 atom 的类型（可能重复计数）走确定性 Monte Carlo fallback：seed 由
signature + density + analyzer version 派生（不含 ruleset fingerprint，保证同几何跨
RuleSet 可复用缓存）；每个起点先用 `set` 对目标格去重再累加，重叠 atom 不会重复计数；
结果可复现，只在静态分析期运行。

### movement graph

空棋盘 directed movement graph：顶点为棋盘格，边为空棋盘一步可达。指标包括
`average_out_degree`、`reachable_pair_ratio`、`average_shortest_path`、`diameter`、
最大 SCC 占比；不连通图不伪造有限 diameter（记录 reachable ratio）。8×8/9×9 精确计算，
超大棋盘用确定性采样 BFS（固定样本源）。

### 基础能力分与归一化

```
raw = Σ w_ρ·m(ρ) + w_c·coverage + w_r·reachable_ratio + w_d·path_efficiency
```

权重集中定义在 `EvaluationConfig`（通用超参数，非棋种知识）。普通非 anchor 类型按中位
`raw` 归一化到 `normal_piece_median_value = 1000`；只有一个普通类型时其值为 1000；raw 全零
的退化类型至少为 1。anchor 不参与 material 归一化、价值为 0。

### board / hand / promotion 值

* 盘上 material 用 `board_value_by_type[current_type]`（升变后按当前能力估值）；
* hand 用 `hand_value_by_base_type[base_type]`（被吃后降格，v0 将棋式语义）；
* promotion 期权静态预计算 `promotion_gain = max(0, max(board_value[target]) - board_value[self])`，
  叶节点只做轻量 zone 进度修正，不在节点里重复分析 promotion target。

## 两级静态缓存

1. `MovementCapabilityProfile`：只依赖棋盘尺寸 + canonical movement signature + analyzer
   version + config，不同 RuleSet 中几何相同的类型可复用。
2. `RuleSetEvaluationProfile`：依赖 ruleset fingerprint + evaluator version + config hash，
   包含全部 piece profile、board/hand/promotion 查表。

内存缓存（LRU、线程安全、可注入）；可选磁盘缓存为版本化 JSON（原子写 temp+rename；损坏、
schema/version/config/fingerprint 不匹配自动失效并重算；默认用户缓存目录；不提交进 Git）。
搜索热路径只查表，不重建 profile。

## 动态评价

叶节点评价 = 盘面 material（current type）+ hand material（base type）+ 轻量动态项：
动态 mobility（`pseudo_attacks` 计数差）、anchor escape squares 差、promotion zone 进度
（在区内/一步可入区），并统一返回当前行动方视角（negamax 友好）。动态项权重较小，避免覆盖
静态 material。

## AlphaBeta 搜索

* negamax + 迭代加深（全窗口，第一版不用 aspiration window）；
* 预算：depth / nodes / time / cancellation；节点计数在节点入口检查，时间/取消每 128 个
  普通节点 + qnode 检查一次（qnode 也计入 node limit）并在每轮迭代边界检查；时间模式只设
  `max_time_seconds` 死线（无固定 nodes/s 上限），固定 nodes 预算仅在无时钟/显式配置时使用；
  预算中止用内部 `SearchAborted` 异常快速展开，只用于中止；
* 终局经 Core 正式 `terminal_result`（GameState.terminal_status），mate score 带 ply 距离
  （更快赢优先、更晚输优先），stalemate/repetition/max_ply 为 0；
* TT：EXACT/LOWER/UPPER、mate score 存/取归一化、generation + depth-preferred 替换、容量
  有界；`probe` 无条件返回任意深度 entry，浅层 entry 的 best move 仍用于 move ordering，
  仅当 entry 深度足够时才应用 bound/cutoff；TT key 包含 ruleset fingerprint + position key
  + repetition counts（避免重复历史混用）；
* move ordering：TT 最优着法、MVV-LVA 捕获（用 profile 值）、promotion、killer、history、
  canonical string 决胜（确定性）；
* quiescence：非将军节点保守版只扩展捕获 + 升变（checking drop 第一版当 quiet，文档记录）；
  被将军节点禁止 stand-pat，改为扩展全部合法解将招；
* 走子生成：搜索热路径使用 Core 公共 `legal_successors(state, compiled)`（一次生成全部合法
  `(action, child_state)`，避免对每个 child 重复 movegen），动作集合与 `legal_actions` 完全一致。

## 搜索位置与历史语义

搜索直接使用 Core 的不可变 `GameState` + `legal_successors` 返回的 child state（不重放整盘
历史）；repetition_counts 由 Core 携带，TT key 与终局判定都保留 repetition/history 语义。

## 与 UI 的边界

AI 包完全不依赖 PySide6。未来 UI 可创建 `AlphaBetaPlayer`，传入当前 `GameSession`、
`SearchLimits` 与 `CancellationToken`，获得 action/PV/score/statistics；不要在 GUI 主线程阻塞
搜索，完整 Human vs AI 界面留给下一阶段。

## 未加入的高级剪枝

null-move、LMR、futility、razoring、singular extension、多线程、选择性剪枝；quiescence 的
checking-drop 扩展；Monte Carlo fallback 仅覆盖重叠/混合 atom 类型；动态 mobility 模式较简。

## 当前实现 vs 设计规格的差距（v0.5 如实记录）

以下指标当前实现比冻结时的启发式设计规格更简，属于文档化的“当前实现”，不代表已完整进入
最终评价：

* **promotion zone**：`Evaluator` 从“空棋盘无前向移动”推导升变区，而不是直接使用编译后的
  `promotion_allowed` mask；自定义 promotion 规则下可能不准确。
* **hand value**：`drop_freedom_ratio` / `drop_mobility` 已计算并存入 profile，但 hand value
  目前仍主要是 `board_value × hand_weight`，drop 指标尚未参与估值。
* **dynamic mobility**：实际使用的是双方 `pseudo_attacks` 去重格数之差，更接近 attack
  coverage，不是每个棋子的 mobility 总和。
* **anchor escape**：只统计空目标格，忽略安全捕获；且在原局面直接检查攻击，未考虑 anchor
  移走后 ray 攻击线变化。

另：时钟语义是非对称的（AI 超时判负、人类永不判负），这是产品决策而非实现缺陷；UI 已明确
标注“AI 超时判负；人类时钟仅供参考，永不判负”。

## 搜索实验框架（0.6.0）

### SearchTuning 与消融

`SearchTuning`（frozen dataclass）把高级搜索技术做成独立开关：`use_pvs`、
`use_aspiration`、`use_staged_move_picker`、`use_countermove`、
`use_mate_distance_pruning` 默认 False，`use_root_tactical` 默认 True（只影响 fallback）；
另有 `check_evasion_max_depth`、aspiration 参数、history 上限与 quiet 分桶数。桌面 UI 使用
默认值；benchmark profile 逐个开启并测量，功能不会因“理论上更高级”而自动进入 UI。

### 搜索热路径

* PVS：首候选全窗口，后续候选 null-window，落在 `(alpha, beta)` 内才重搜；
* aspiration：深度 ≥ `aspiration_start_depth` 且分数远离 mate 时用窄窗，fail-low/high
  加倍扩窗、连续两次失败回退全窗（同深度循环，窗口成功才推进深度）；
* root tactical scan：ID 前扫描全部根后继（先找将死立即返回，否则按快评取最优），无完整
  迭代时 fallback 用扫描最优而非字典序首动作；扫描计入节点预算；
* staged move picker：TT → 有利捕获（rule-derived MVV-LVA）→ 高收益升变 → killer/
  countermove → history 分桶 quiet → 普通 quiet → 亏损捕获；单次分类、按阶段惰性产出。
  checking 动作阶段因需逐动作将军探测（一次 movegen）暂缓，文档记录；
* countermove：`prev_action → response` 表（Action 对象作 key），beta cutoff 时记录；
  history 用 `(side, Action)` 键并封顶 `history_max`；
* mate-distance pruning：`negamax` 入口把窗口钳到 `[-MATE+ply, MATE-ply-1]`，精确不改变
  结果；
* check-evasion qsearch：到达 `check_evasion_max_depth` 或 qnode 上限时抛 `SearchAborted`
  中止当前迭代（不返回静态评价），`run_root_search` 返回上一个完整深度或 fallback。

### Benchmark 设计

固定 seed RuleSet 套件（`generic_chess.ai.benchmark.suite` 的 `DEFAULT_SUITE`）× 每个
RuleSet 的固定开局（用 `random.Random(f"{seed}:{plies}")` 确定性重放）× 双方换先 × 预算档位。
`run_benchmark` 通过 `GameSession` 公共语义落子，按 Core 终局判胜负；手数上限记
`unresolved`；fallback 或超时（`max(50ms, 5%)`）的局不计入棋力得分；`events.jsonl` 记录每手
诊断，`summary.json` 汇总 eligible/unresolved/fallback/换先配对，`--resume` 跳过已完成对局。

### 与 UI 的边界

AI worker 只读 GUI 线程冻结的 `SearchSnapshot`（session/limits/fingerprint/root
key/generation），结束后按 snapshot 与当前 generation/root key/fingerprint 比对丢弃陈旧结果；
`SearchBackend` 协议隔离搜索实现，UI/benchmark 不依赖具体后端。

### 后续阶段（Phase 3-5，本设计不含实现）

Phase 3 热路径：增量 material/hand/promotion evaluator、fast/exact 评价边界、可复用攻击
scratch、compact action key（避免热路径 `str(action)`）、增量 position hash。Phase 4 保守战术
组件：generic SEE（先只排序）、有严格上界后的 lazy full evaluation、bounded mate prover、
checking-action 分类。Phase 5 高风险选择性搜索：LMR、reverse futility、razoring、null move；
每项默认关闭、单独 profile、多 RuleSet 类别测试、与未剪枝搜索小深度一致性检查。
