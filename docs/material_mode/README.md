# Material Score 后端

用户授权的独立产品后端，分支 `codex/material-mode-backend`。不修改旧 Core、UI、固定 AI 基线或神经网络研究。本包只需要 Python 标准库及仓库现有代码；不需要 Qt、Torch、原生扩展、Slack 或研究 session。此分支的新增后端范围来自用户明确实施计划；原 UI-only 策略文件保留不改。

## 快速开始

```python
import json
from generic_chess.material_mode import (
    ModeRules, ModeSession, BasicTwoPlayer, example_rules,
    BuyPiece, BuyAndDrop, BoardMove, DropMove, Square,
    action_to_dict, action_from_dict,
)

# 双人8x6；四人则 example_rules(players=4)，默认8x8。
session = ModeSession(example_rules())
public_state = session.snapshot().to_dict()
public_rules = session.rules.to_dict()
legal = [action_to_dict(a) for a in session.legal_actions()]

# 人类/未来HTTP适配器提交一项返回的合法行动。
session.submit(action_from_dict(legal[0]))

# 双人基础AI；不会修改session，调用方负责接受结果。
ai = BasicTwoPlayer(seed=0)
captured_state = session.state
decision = ai.choose_action(session)
if not decision.cancelled and decision.action is not None and session.state is captured_state:
    session.submit(decision.action)

saved = json.dumps(session.to_record(), ensure_ascii=False)
restored = ModeSession.from_record(saved)
assert restored.state == session.state
session.undo()
session.redo()
```

文件 `examples/material_mode/two_player.json`、`four_player.json` 是完整规则，不是棋谱：

```python
from pathlib import Path
rules = ModeRules.from_dict(json.loads(Path('examples/material_mode/four_player.json').read_text()))
session = ModeSession(rules)
```

示例目录包含普通一格前跳、Knight、Rook、Bishop、Queen 和 anchor；名称不参与计价。初始一方为底边的 Knight、anchor、一格前跳子，其他方由旋转产生。`ModeRules.from_ruleset(old_rules, players=...)` 可提取既有普通 Leap/Ray 类型和 owner0 阵型，清除升变属性；新模式的经济、打入及终局设置另行配置。含条件 semantic actions 的旧规则不能冒充普通移动导入。

## 规则与计价

`ModeRules(width, height, players, piece_types, formation, ...)` 接收现有 `PieceType` 和 `Placement(type_id, Square)`。`formation` 是底边朝内的一方阵型，恰好一个 anchor，anchor 在底边。双人旋转180度，四人方盘旋转90度；重复占格或任何初始 anchor 被攻击会拒绝创建；四人阵型还必须使每方有合法开局行动，避免全体困毙而按顺序产生任意胜者。方向/轮转为：双人0南、1北；四人0南、1西、2北、3东，顺时针轮转。初始钱包和手持为空。

参数默认值：`ray_multiplier='0.6'`、`purchase_penalty=True`、`repetition_limit=4`、`max_ply=512`、`starting_player=0`。四人必须方盘。multiplier 可为任意非负有限十进制值，包括0；每次购买仍占一回合。

普通子价格 = 不同有效 Leap 位移数 + multiplier × 最大空盘 Ray 可达格子并集大小。Leap 必须在该棋盘上存在有效起终点，不按当前边角位置折价。Ray 遍历所有起点，考虑方向、边界和 max_steps；同一部分内部重复不重复收费，两部分之间允许重复计价。价格整局固定，不随遮挡或位置改变。

| 棋子/棋盘 | 价格 |
|---|---:|
| Knight | 8 |
| Rook 8x8 | 8.4 |
| Rook 20x20 | 22.8 |
| Rook 8x6 | 7.2 |
| Bishop 8x8 | 7.8 |
| Queen 8x8 | 16.2 |

钱包内部是整数最小单位，`rules.score_scale` 给出每分单位数；默认0.6时每分10单位。`state.balances` 和 AI 的 `score_units` 都是内部单位。`snapshot().balances`、目录价格和 `session.price(type_id)` 是面向UI的精确十进制字符串，例如`'0.4'`，禁止按整数截断。Anchor 无购买价格，也不参与 material 评价。

## 行动、会话与只读状态

- `BoardMove`：沿用已有几何，不能吃任何 anchor，不能留下自己的 anchor 被攻击。吃掉普通敌子/中立资源后按完整固定价格入钱包，不直接送入持子。
- `BuyPiece(type_id)`：扣除价格、公开增加一枚持子并结束回合；被将军时不能用不改变棋盘的购买应将。
- `DropMove(type_id, square)`：从自己持子减少一枚，在空格放置；最后一排、同列重复、直接将军/将死均允许，仍须保护自己 anchor。
- `BuyAndDrop(type_id, square)`：仅关闭 purchase_penalty 时合法；扣款及落子原子完成，一共占一回合。
- `resign()`／`Resign()`：当前玩家认输，记入棋谱。没有额外的免费购买、批量购买或普通 pass。

调用接口：`legal_actions()`、`submit(action)`、`resign()`、`undo()`、`redo()`、`price(type_id)`、`snapshot()`、`to_record()`、`ModeSession.from_record(dict_or_json)`。会话是单写入者，状态及快照不可变；非法行动不扣款、不截断redo或修改状态。撤销后提交新行动会丢弃旧redo分支。棋谱自含规则/价格/初始阵型和所接受的行动；加载时重新验证并重放，不信任外部提交的终局或钱包。

未来UI读取开局规则一次，以获得全部 Leap/Ray 定义；之后使用 `snapshot().to_dict()` 获取全体公开余额、持子、目录价格、当前玩家、结果和淘汰事件。棋盘 row-major，索引=`rank*width+file`。格子为None或包含 `type_id/owner/former_owner/status`；status是`active`、`neutral`或`frozen_anchor`。中立及冻结格子的owner为None、former_owner保留来源玩家。没有隐藏持子或隐藏分数。`action_to_dict/from_dict` 负责现有移动/打入和新购买行动的格式，不需要UI复制合法性逻辑。

## 四人终局

仅在轮到某方时判定其全部合法行动，包含购买、打入。其他玩家有机会在该回合前改变局面，救下此前被将军者。将死/困毙者淘汰；钱包和持子清零，盘上普通子中立化且不再攻击/移动，anchor冻结且不再攻击、不能被吃。Frozen anchor仍占格并挡射线，Leap可以跨过但不能落在它上面。

双人正常结束保留钱包/持子供查看，不执行四人战利品中立化。连续淘汰自动跳过，最后一人获胜；没有将死奖金、结盟或战利品自动继承。双人将死获胜、困毙和棋。每个提交行动（包括购买或认输）计一个ply，自动跳过/淘汰不另加ply。完整位置重复包含棋盘、持子、钱包、存活状态和行动方，购买不会被当成棋盘没变的重复。重复/限步和棋的drawn_players仅含尚存玩家。

## 双人AI与验证

`BasicTwoPlayer.choose_action(session, limits=None, cancel_token=None)` 返回 `ModeDecision(action, score_units, completed_depth, nodes, cancelled)`。复用现有 `SearchLimits`、`CancellationToken`，默认深度2、2000节点、1秒协作式预算，保留完整根迭代；未完成首层时返回合法候选，取消时action=None。会话不被搜索改变。四人调用明确抛出NotImplementedError。

评价只有双方“普通盘上子+持子+钱包”点数之差，胜负值严格大于初始 material 总量，无位置经验/NN/Qsearch/训练或强度目标。相同得分用固定种子随机选，允许AI在等分选项中购买。计时是协作式边界，不是操作系统硬实时承诺。异步UI应在提交前确认会话仍是搜索捕获的状态，并在重新开局/撤销时取消旧任务。

```powershell
python -m pytest -p no:cacheprovider tests/product/material_mode -q
python -m pytest -p no:cacheprovider --basetemp .gc_cli_tmp_material_pve tests/product/test_ui_test_pve.py tests/product/test_ui_controller.py tests/product/test_ui_lifecycle.py tests/product/test_ui_app.py -q
```

当前验收：最终联合回归129项全部通过，其中新模式44项通过，包括96回合四方混合行动重放、真实小数购买、AI实际吃子/购买/将死打入。旧冻结源码和UI/PVE回归通过；首次9个旧测试因系统临时目录WinError5在setup失败，使用全新检出内临时目录重跑9项通过，未修改旧代码/测试期望。此包不提供网页、HTTP服务、账号/联网对局或四人AI。
