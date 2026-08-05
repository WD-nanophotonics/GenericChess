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
