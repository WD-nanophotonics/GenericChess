# Latest endorsed project direction

Source: project ChatGPT comment1792751845.867269,2026-10-23. Raw exact revision retained privately; project-only text below. Applied under the user standing instruction that latest ChatGPT project comments set the next direction after bounded work closes.

CHAT_Comments | GenericChess 用户最新研究计划：先建立可校准的规则探索器，再推进逆向设计 | 2026-10-23
收件对象：PRIMARY_SANDBOX、DEV_AUX（两名现有Agent；请在下一次原有工作节奏中分别评估、协调，不要求实时回复）。

【用户的核心决定】
研究不应只追求“ABP能打赢Random”或直接搜索一个高分ruleset，而应先回答：我们能否可靠地判断一套未知规则有哪些性质？建立“精确/半精确规则真值 → 廉价探索器预测 → 与真值比对 → 找出误差来源、改进探索器 → 未见规则盲测”的循环，待判断器的分辨力经验证后，再让它指导inverse design。这是原纯Leaper五轨道及通用学习主线的科学深化，而非另起产品项目、也不是需要先制造一个单标量“好游戏”分数。

【动机与已证边界】
PRIMARY已测多种4x4纯Leaper：最初10码AB512对Random为64W96D0L/160局，另40码为516W108D16L/640局，说明很多规则上规则导出Static-ABP明显强于Random。但这不能定义“好规则”：一步/两步杀、对手极弱、终局和棋密集、对特定布局或座位高度依赖，都可能造成误导。AUX已有大量<=3/4子精确图，证明真实封闭死区、WDL岔路、同分与搜索深度问题。PRIMARY最新8f1f9e5的六规则inverse筛选在新前缀上guided资源效用3/16、非引导1/4（负差-1/16），且先手机会分布改变使旧role guard失效。这个负结果尤其提示：先证明规则评估指标对真实性质和分布有辨识力，不能单靠样本内Pareto挑赢家。

【两个互不混淆的真值层次】
1 博弈论/结构真值：给定RuleSet、完整history（含重复计数、rule max-ply、剩余时钟），每个合法动作的精确WIN/DRAW/LOSS或保守界、可达终局、强制胜深度、结构性封闭无法决胜区域。部分图不可解时只给证书/界/UNKNOWN。
2 特定策略真值：在同规则、同初始历史分布μ、已冻结Random/FLOOR/ABP及对手协议下的实际W/D/L分布、终局时间、重复率和局部轨迹；可小规模全枚举策略诱导转移，或通过独立有界对局估计。规则确定性≠Random政策没有随机性；“minimax DRAW”和“给定对手大概率DRAW”不是一个事实。
尤其必须区别：A. 任何合法双方合作路径都无法决胜的结构deadzone；B. 有出口但有限棋手反复返回的政策local attractor；C. 在某一步丧失强制保证WIN/DRAW、但仍可能靠对手失误翻盘的临界分支；D. 后续合法所有行动均导致同结果的强不可逆性。这些定义不许混写。只看Position图SCC不得忽略重复历史与规则时钟。

【第一版规则性质向量（先不合成总分）】
按rule、布局/开局分布、对手和预算分别记录：(i)真实决胜/和棋/各终局原因；(ii)结构deadzone的可达性与自然访问率；(iii)局部政策循环及有限搜索能否逃离；(iv)精确不同WDL行动的密度、关键早期转折点及强制胜深度；(v)Random→FLOOR→StaticAB及D1/D2/D4、N128/512/2048的实际辨识；(vi)Static/Unit/Mobility/TD在共同条件下是否带来真实效用而非仅分数/PV变化；(vii)未知覆盖率、预测置信/校准与完整计算成本。UNKNOWN、未尝试、caller截断、真正规则和棋分开，PV叶分不冒充精确WDL。

【探索器的迭代：以可证伪的预测取代过度工程】
版本E0先使用已有廉价特征：轨道编码、空盘运动图、单子将杀能力、根的一步胜、自然对局结局/长度/重复、AB对Random/FLOOR和预算阶梯；在不读取测试真值前，冻结对规则性质的预测及不确定性。
由AUX的精确真值系统给出同一批小规则上可核验的答案。比较规则级/历史级预测误差、排序、漏报关键WDL岔路、deadzone/attractor误判和信息成本，记录清楚失败案例。E1才按具体误差加入对捕获后子力的局部求解、循环逃离验证、局面抽样或选择性exact query等；在未见规则/布局上与E0等成本对照。探索器不等于AlphaBeta棋手：可让ABP提供特征，但“探索器变好”必须是对规则真实性质的预测/校准和每单位计算信息收益改善。后续再让它主动选择下一笔局面查询，最终推进inverse/Pareto，并与等成本非引导规则选择比较。

【继续保留现有双Agent分工】
PRIMARY_SANDBOX：唯一负责五轨道规则编码/生成、分层规则样本、合法初始/前缀μ、Random/FLOOR/ABP便宜对局、探索器E0特征/预测/成本/后续inverse。基于现有脚本做最小规则级冻结预测输出，不重建求解器。
DEV_AUX：唯一负责冻结规则与完整history的Core精确WDL、可合作决胜性与结构deadzone、历史/政策循环区分、关键行动真值/证书与成本，建立truth/coverage分母及对PRIMARY预测的离线评测；不得用oracle挑选PRIMARY的预测规则、经验TRAIN起点或调已有棋手默认。探索器内的真值调用仅作为明确标记的独立诊断/校准步骤。
双方交换最小契约：rule fingerprint、规范轨道掩码、完整初始history和μ、抽样/角色/对手/seed、rule与caller时钟、预测向量/置信度、精确标签或上下界与coverage、实际节点/时间、执行SHA和来源；跨规则split先冻结，避免同一码不同换名/布局泄漏到测试集。

【第一轮最小可实施验证（建议，不授权无界计算）】
先利用现存3x3/4x4已闭合组件与历史报告，由双方协定约8–12组机制不同的小规则作正负对照：开局快杀、长期/结构和棋、可退出策略循环、具有D1→D4实际行动WDL改善等。首先盘点哪些是真正已求解，不能要求每个4x4六子起点都完成全图。预先按规则族冻结校准集与规则级留出集；写明完整历史标签和政策样本分母。E0只读现有前向记录能得出的预测，AUX离线核对精确真值，输出最少一个新发现的假阳性和一个假阴性及后续能够区分它们的最小检查。若无法形成足够的真值对照，则保留UNKNOWN并缩小任务，不扩大大图证明或所有961/4495组合扫描。小范围通过后再做规则级新holdout、主动探索和inverse，不把已见规则上的改善称泛化。

【工作/论文/执行】
正在进行且有预登记停止条件的研究可安全收尾，不要求立刻打断、创建worker、重置cap、增加任务频率或修改对方分支。本用户决定影响下一轮研究优先级：应先验证“我们能正确描述规则”，才谈大规模逆向选规则；当前已有inverse负例也应保留为方法校准教材。项目已有独立论文初稿分支research/genericchess-manuscript，后续应把该真值校准层纳入论文学术叙事，但此Slack消息不要求立即编辑PDF或另起论文项目。希望两名Agent在各自下一个正常会话中给出：能复用的已提交模块/真实已求解规则、小型E0评测具体设计、预计完整成本与明确停止条件、以及双方数据交接处缺的最少内容。研究价值以真实性质识别率和新规则泛化为核心，不以提交量/跑局数为目标。

研究依据：
<https://github.com/WD-nanophotonics/GenericChess/blob/7c0d3e55d6424945ab166b06351e16823cda9b70/docs/research/LEAPER_FORWARD_DESIGN_20261022.md|github.com/WD-nanophotonics/GenericChess/blob/…/LEAPER_FORWARD_DESIGN_20261022.md>
<https://github.com/WD-nanophotonics/GenericChess/blob/cad06a0ec73984849b1efe63efbbe5555ebf525f/docs/research/LEAPER_TIE_TRUTH_AND_FREE_PRIORS_20261023.md|github.com/WD-nanophotonics/GenericChess/blob/…/LEAPER_TIE_T…>
<https://github.com/WD-nanophotonics/GenericChess/blob/8f1f9e5f977e1baba0e5a3cd14d74b7ea0351130/docs/research/LEAPER_INVERSE_SELECTION_TRANSFER_20261023.md|github.com/WD-nanophotonics/GenericChess/blob/…/LEAPER_INVER…>
请按最新直接用户意见处理，原有限角色/stop/预算/定时边界保持。
