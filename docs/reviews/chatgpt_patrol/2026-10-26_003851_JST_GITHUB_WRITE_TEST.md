# ChatGPT独立审查：纯Leaper的数学编译应成为搜索器研究主线之一

审查编制时间：2026-10-26 00:38:51 JST（日本时间）。性质：2026-10-26 第二次、一次性定时 GitHub 写入验证，内容同时是一份独立研究审查。写入前 `sandbox` HEAD：`07875ca38f44d5086a0fa394c21583e3c829bfd2`。本次只检查远端材料，不运行新的搜索、对局或性能实验；不会替代 PRIMARY 的具体研究结论，也不修改代码、原研究、Agent 状态或调度。上一篇审查已经保存于 [00:26:51 JST 的独立审查](https://github.com/WD-nanophotonics/GenericChess/blob/sandbox/docs/reviews/chatgpt_patrol/2026-10-26_002651_JST_GITHUB_WRITE_TEST.md)；本文是再次核查代码与研究路线，并额外评估已经记录的 Native 搜索成本及可证伪条件，不冒称出现了新的实验数据。

## 一、研究判断（B2：独立方向监督）

用户此前已多次将“纯 Leaper 优先”和“利用其数学结构简化计算”设为方向，不能因为 PRIMARY 近来集中报告 p49/p53 的 D3、D4、D5、D6 决策变化，就把研究主线缩窄成修复这两例。有限跳跃向量与当前五个基础对称轨道 `(1,0),(1,1),(2,0),(2,1),(2,2)` 允许把单棋种的几何移动关系编译为有限图/整数掩码。普通 Leaper 不存在中途阻挡，攻击关系可以预先表述为依棋种、棋格、双方朝向的有限矩阵。后续状态的可落子性仍依赖占据情况和完整棋规；几何简化不得冒充胜负判定。

监督者有义务独立判断研究问题是否切中最终目标。当前[主线记录](https://github.com/WD-nanophotonics/GenericChess/blob/07875ca38f44d5086a0fa394c21583e3c829bfd2/docs/research/LOCAL_MAINLINE.md)仍安排 anchor-term 消融的进一步消费验证；那可以作为有约束的科学实验，但没有充分证据成为唯一高优先级路线。更有区分度的问题是：经过严格准入的纯 Leaper 子集，能否在不改变决策、搜索算法和完整终局语义的情况下，把每个节点的成本大幅降低？如果能，再利用同一时间预算进行跨规则棋力检验；如果不能，应及时停止该具体优化，不宜仅凭数学形式漂亮继续工程化。p49/p53仅留作回归和视野效应诊断，不以已知 WDL 标签反向特化搜索器。

## 二、工程代码检查（A：已有实现与可测缺口）

不能重新发明“预先计算从某格能跳到哪格”。[CompiledRuleSet](https://github.com/WD-nanophotonics/GenericChess/blob/07875ca38f44d5086a0fa394c21583e3c829bfd2/generic_chess/rules/compiled.py)已提供 `leap_targets`、`empty_mobility` 等表；[五轨道生成器](https://github.com/WD-nanophotonics/GenericChess/blob/07875ca38f44d5086a0fa394c21583e3c829bfd2/scripts/leaper_design.py)已通过 1…31 的 mask 构造轨道组合；[Native legality](https://github.com/WD-nanophotonics/GenericChess/blob/07875ca38f44d5086a0fa394c21583e3c829bfd2/generic_chess/ai/alphabeta/native_legality.py)已有编译后合法性、将军、availability 查询以及 check-to-availability 的一次性输入复用；[search_runtime](https://github.com/WD-nanophotonics/GenericChess/blob/07875ca38f44d5086a0fa394c21583e3c829bfd2/generic_chess/core/search_runtime.py)已有用于普通 `BoardMove` 的触及格增量哈希。这些是既有工作，不能列作候选方案的新发明。

可以继续检验的，是 **整体调用成本** 是否还包含可消除的通用解释与差分开销。[Core attacks](https://github.com/WD-nanophotonics/GenericChess/blob/07875ca38f44d5086a0fa394c21583e3c829bfd2/generic_chess/core/attacks.py)的通用 Python 攻击查询仍逐棋子查询预计算表；[Evaluator](https://github.com/WD-nanophotonics/GenericChess/blob/07875ca38f44d5086a0fa394c21583e3c829bfd2/generic_chess/ai/evaluation/evaluator.py)在启用行动力与王逃脱项时调用两方 `pseudo_attacks` 构建集合；`search_runtime.py` 的 `_semantic_component_diff_hash` 仍比较整张棋盘，而 `SearchPathRuntime._push_impl` 对 semantic 分支会选择这一路径。对符合条件的普通 Leaper，可以考虑编译出位图攻击集合、反向攻击来源掩码以及仅更新起点/终点的完整局面状态，从而减少重复分配和循环。但必须先剖析当前 **实际生产搜索** 的计时占比及 Native 边界成本，不能把通用 Python 代码的局部低效直接等同于实际热点；还必须保留原有 Core 的 fallback。

一个需要形式化证明才能执行的捷径：若当前己王未被将军、己方走非王普通一步、所有敌子攻击均是固定 Leaper 几何且对手棋种/位置至多因本次吃子减少，则敌方攻击己王的可能性不会增加；可以尝试免除某类重复王安全复查。若初始已被将军、王移动、drop/升变/复合效果/额外状态触发/射线走法混入，就不能沿用这个结论。即使在可认证子集内，合法行动的落点、checkmate/stalemate、完整历史与反复、时钟、TT身份和精确回退仍要逐项等价于原Core；一个局部定理绝不授权删除这些检查。

## 三、数学与证据边界（B1：不夸大几何或加速的解释）

[Knuth《Leaper Graphs》](https://arxiv.org/abs/math/9411240)讨论的移动图、连通分量与数论约束，提示可在规则编译阶段求出固定模类、可达距离或不变量；但五轨道组合需另行验证推论。几何上走不到某格，不等于包含对抗、吃子、历史终局的局面必败或必和；没有完整证明不能把图性质直接当 WDL 剪枝条件。

[Native DEFAULT/PVS 原始报告](https://github.com/WD-nanophotonics/GenericChess/blob/07875ca38f44d5086a0fa394c21583e3c829bfd2/docs/research/LEAPER_NATIVE_DEFAULT_20261025.md)给出可核查的边界：64个同一规则、已曝光的完整历史的 50k-event 配对调用，从 839.615s 降到 519.211s（-38.16%），动作、分数和工作事件没有变化。这是受限输入的等工作成本进步；固定 1.5s 预算下双方仍为 62/64 源标签正确，24局实际对弈都以规则和棋结束，因此没有跨规则棋力改善的证明。报告还记录有 28,184 次 runtime push、20,694 次 noisy-child 分类，且 qsearch 已经在同一次 push 中完成分类和后续递归，不能以“消灭重复push”为假设重做一遍。此外一次附带剖析将耗时从 2.138s 扰动到 5.638s，其采样占比不能直接当无扰动的生产热点。上述数值取自仓库原始报告；本轮没有独立重跑，也没有证明全部Leaper规则具有同样加速。

## 四、最小可证伪比较和停止条件

选取 **事先冻结的 3–5 套不同纯Leaper规则**，每套预先封存若干包含完整GameRecord的状态（包括将军、吃子、临近重复/计步阈值和正常中局）。同一仓库SHA、CPU环境、编译开关、AlphaBeta/PVS/Q/TT/评价、启动条件与完整Core终局逻辑下，配对运行“现有 Core+Native”与“可证明等价的纯Leaper编译路径”。优先逐格比较棋盘/行动/攻击/合法后继/可撤销路径/时钟/重复次数/终局/TT身份，再比较完成相同深度时实际 wall、CPU、总启动+打包时间、nodes、qnodes、完成深度及超时删失；给出开销分解，不能把较高 NPS 当作棋力增益。

明确拒绝标准：出现任何完整规则不等价、非法行动或历史身份差异，立即停止并回退专用路径；若只有子过程微基准加速而整体搜索无稳定获益，也暂停该方向。只有证明完整搜索节省真实时间后，再用固定预算、交换先后手、预登记对手与未见过的Leaper规则进行配对对局，比较实际 W/L/D 与置信区间。若当前评价消融或 p49/p53 研究继续消耗时间而无泛化信息收益，监督审查应明确建议暂缓，不能继续被PRIMARY已选的局部问题带动。这是研究建议，并未在本次运行派工、执行或修改任何主线。
