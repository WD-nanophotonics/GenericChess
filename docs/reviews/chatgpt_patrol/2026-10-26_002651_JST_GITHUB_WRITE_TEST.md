# ChatGPT独立审查：纯Leaper的数学编译应成为搜索器研究主线之一

- 审查日期：2026-10-26 00:26:51 JST（一次性 GitHub 自动写入测试）
- 写入前 sandbox HEAD：`fb9cda2c9bbff79e9b71dc87c02dbfa567205a7f`
- 范围：独立研究方向、工程/架构与科学证据审查。只新增本文件，不修改代码、原研究记录、角色状态或运行配置。
- 方法：基于该固定 SHA 的远端源码、`docs/research/LOCAL_MAINLINE.md` 和 `docs/research/LEAPER_NATIVE_DEFAULT_20261025.md` 的只读检查；未在本轮运行新的搜索、性能基准或对局。PRIMARY 的自述与本人复验必须分开。

## 一、方向判断：应从规则编译的计算结构出发，而非从 p49/p53 出发

用户早已要求纯 Leaper 优先，并曾明确提出借助 Leaper 数学结构简化通用搜索；审查者此前未充分沿这一方向独立推进。纯 Leaper 并非仅是便于生成小型棋力实验的 toy ruleset。固定的有限跳跃向量集、当前实验的五个基础对称轨道 `(1,0),(1,1),(2,0),(2,1),(2,2)`、不受中途阻挡的移动关系，构成可在编译时预处理的有限图与计算算子。若用位置位图、按棋种和格子的攻击掩码、反向攻击源表、局部状态转移，可以尝试将通用规则解释与重复状态检查减少为少量局部更新和位操作。须把完整棋规当作语义权威；具体加速机制要以真实执行数据检验。

`LOCAL_MAINLINE.md` 仍把 p49 的 D3 正确/D4 错误、B 分支静态分数变动和 anchor-term 消融列在主线判断附近。D3 与 D4 结果非单调，只能提示搜索视野、叶评价或搜索边界相关的不确定性；它们不能单独定义搜索器的总体质量。p49/p53 应保留为诊断/回归输入，禁止以它们的事后 WDL 标签特化搜索、拟合参数或据此声称跨规则棋力提升。监督职责包括主动比较PRIMARY没有提出的技术路线，不以其最新任务清单划定审查范围。

## 二、现有实现与可验证的工程机会

不能把“事先算好Leaper从哪里跳到哪里”包装为新发现：[`generic_chess/rules/compiled.py`](https://github.com/WD-nanophotonics/GenericChess/blob/fb9cda2c9bbff79e9b71dc87c02dbfa567205a7f/generic_chess/rules/compiled.py) 已明确列出 `leap_targets`、`empty_mobility` 等预计算结构；[`scripts/leaper_design.py`](https://github.com/WD-nanophotonics/GenericChess/blob/fb9cda2c9bbff79e9b71dc87c02dbfa567205a7f/scripts/leaper_design.py) 已把五轨道编码为 mask；[`generic_chess/ai/alphabeta/native_legality.py`](https://github.com/WD-nanophotonics/GenericChess/blob/fb9cda2c9bbff79e9b71dc87c02dbfa567205a7f/generic_chess/ai/alphabeta/native_legality.py) 已有 Native transient legality、check 与 availability 服务，并以 Core 负责完整终局/历史优先级；[`generic_chess/core/search_runtime.py`](https://github.com/WD-nanophotonics/GenericChess/blob/fb9cda2c9bbff79e9b71dc87c02dbfa567205a7f/generic_chess/core/search_runtime.py) 已有对普通 BoardMove 只更新触及格的 legacy 增量哈希。建议是在这些已有设施之上验证新的**完整搜索热路径**，而非重做现有表。

仍可核查的具体缺口：[`generic_chess/core/attacks.py`](https://github.com/WD-nanophotonics/GenericChess/blob/fb9cda2c9bbff79e9b71dc87c02dbfa567205a7f/generic_chess/core/attacks.py) 的通用 Python 攻击查询仍按棋子/预计算表迭代；[`generic_chess/ai/evaluation/evaluator.py`](https://github.com/WD-nanophotonics/GenericChess/blob/fb9cda2c9bbff79e9b71dc87c02dbfa567205a7f/generic_chess/ai/evaluation/evaluator.py) 在启用动态行动力/王逃脱特征时仍构造双方攻击集合；`_semantic_component_diff_hash` 在 [`core/search_runtime.py`](https://github.com/WD-nanophotonics/GenericChess/blob/fb9cda2c9bbff79e9b71dc87c02dbfa567205a7f/generic_chess/core/search_runtime.py) 会逐格扫描前后棋盘以寻找变化。这不代表生产搜索必然走这些路径，也没有证明它们目前占主耗时。可尝试为编译器严格认证的“仅普通Leaper、吃子移除、无升变/drop/连锁触发/额外状态改变”子集生成反向攻击掩码及双格局部差分，测量与**现有 Native 实际路径**的对比；跨 Python/Native 打包和恢复的成本必须一并计入。

一个可形式化的安全捷径：若当前王未被将军，执行者移动非王棋子，而敌方攻击集仅由敌方各 Leaper 的位置/类型确定、移动不会改变敌方其他状态，则普通走法保持敌方攻击集或因吃子缩小，己方王不会因“揭开路线”而被新攻击。因此在经过充分准入证明后，此类行动可省掉某些完整王安全复查。若原本已被将军、行动是王移动、规则可触发连锁变化、攻击依赖状态或棋盘中有滑行棋子，上述结论不成立。**不能省略**目标格合法性、终局、重复历史、时钟、完整TT身份与必要的王被攻击判断；须保留Core原始语义对照并审查Native已有优化，避免重复实现。

## 三、数学论文与科学证据边界

Knuth《Leaper Graphs》（[arXiv:math/9411240](https://arxiv.org/abs/math/9411240)）提示可在规则编译阶段研究移动图的连通分量、格点模类、有限图可达距离等。单一 Leaper 的结论不能未经检验直接推广到五轨道的组合；更不能从移动图的不连通或距离下界直接推导完整游戏的胜负和棋 WDL，更不能无完整博弈语义证明即用于搜索剪枝。编译所得的几何性质可先作为安全的运算结构或保守启发式进行验证。

现有[`LEAPER_NATIVE_DEFAULT_20261025.md`](https://github.com/WD-nanophotonics/GenericChess/blob/fb9cda2c9bbff79e9b71dc87c02dbfa567205a7f/docs/research/LEAPER_NATIVE_DEFAULT_20261025.md)报告：开启已有 Native availability + check 后，64个同规则已曝光历史、50k-event 配对查询的总成本从839.615秒降到519.211秒（-38.16%），相同动作/分数/工作事件；1.5秒条件仍为62/64源标注 WDL 正确选择，24盘实际对局均以规则 DRAW 告终。因此这支持特定输入的等工作量运行成本改进，但**没有提供跨规则棋力跃升证据**；实验中存在时间截断、来源标签与完整独立求解不同、同规则历史相关性等边界。作为独立审查，本轮没有复跑上述测试，也没有证明这些耗时由哪条内部子程序支配。

## 四、最小可证伪验证与转向条件

建议先设一个很小的编译内核验证，不启动大规模求解：在 3–5 套结构差异明显的纯 Leaper 规则上，预先冻结规则指纹、若干含完整GameRecord的开局和中局、搜索参数/版本/随机种子、AlphaBeta/PVS/Q/TT/时钟/终局及对手条件。将现有 Core+Native 路径作为基线，以新专用表示为候选，逐个比较合法行动集合及其顺序约束、走棋-撤销与完整历史、王安全、终局/重复/时钟、TT键和搜索结果；完成相同深度与等工作量比较时报告总 wall/CPU、启动与打包开销、nodes/qnodes、完成深度、删失与差异原因。**正确性、完整历史或行动不等价即立即停止**。若只有微基准快而整体查询没有稳定收益，也终止该实现方向，不扩大预算。

如果小样本正确且对完整搜索确实节省时间，下一阶段再在冻结计算时间下进行颜色/初始局面配对的真实对局，加入未见过的规则和已登记停止标准，比较胜负、完成工作量与不确定区间；不可把NPS、单根D3/D4、TT命中率或更深的数字直接认作棋力。若两轮独立巡检后这条或现有PRIMARY路线均没有相关新证据，应显式比较继续微调评价器、转向规则特化计算内核及选择性搜索的预期信息收益、时间/工程/Token机会成本（无数据则不虚构数字），提出应暂缓的路线。当前建议：保留诊断性回归，同时把“可证正确的 Leaper 数学编译是否降低全程搜索成本”列为优先验证课题；不改变PRIMARY的实际工作状态或任务权限。
