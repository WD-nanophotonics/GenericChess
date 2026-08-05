# GenericChess v0 —— 通用棋类/将棋类引擎

一个确定性、无 UI 的通用棋类/将棋类游戏引擎，用于研究随机棋子走法、通用棋类 AI 与跨规则泛化。当前为第一阶段：Core Kernel（确定性规则内核）、RuleSet Schema 与 Compiler（声明/验证/编译）、Generator（带 seed 的规则与初始局面生成）、完整测试、序列化与无 UI 的命令行 smoke demo。

运行时仅依赖 Python 标准库（Python 3.11+）；`pytest` 仅为开发依赖。

## 三层架构

职责严格分离，未来的 UI 与 AI 只允许通过 Core 的公共接口访问合法性判断：

1. **Core Kernel**（`generic_chess/core/`）——只负责棋盘与状态表示、movement atom 语义、攻击判断、check、合法动作生成、捕获、持驹、打入、升变、状态转移、repetition 与终局。Core 内禁止任何随机数。
2. **RuleSet 与 Compiler**（`generic_chess/rules/`）——声明一套具体规则、严格验证、编译相对方向 / ray path / leap target / 升变区 / 打入 mask 为确定查询表，生成稳定的 SHA-256 fingerprint，并提供 JSON 序列化与反序列化。Compiler 只检查规则是否完备、自洽、可执行，不因“好不好玩”拒绝规则。
3. **Generator**（`generic_chess/generation/`）——软性偏好：棋盘大小、左右对称程度、ray/leap 比例、随机棋子走法、初始阵型、升变/打入规则推导、可玩性过滤、seed 复现。所有随机数只出现在 Generator，且使用局部 `random.Random(seed)`，不依赖模块级全局随机状态。

依赖方向：Core/Rules/Generation → **Session**（`generic_chess/session/`）→ **CLI**（`generic_chess/cli/`）。

## GameSession（对局会话层）

`GameSession` 是面向 UI、真人玩家和未来 AI player 的有状态会话层：它把 Core 的不可变 `GameState`/`Action` 包装成可交互、可记录、可认输、可重放的对局对象，并且只通过 Core 公共语义工作（`legal_actions` / `apply_action` / `terminal_result` / `position_key`），绝不触碰私有执行器。Session API 只从 `generic_chess.session` 导入，不进入 `generic_chess` 顶层。

```python
from generic_chess.session import GameSession
from generic_chess.session.serialization import serialize_game_record, deserialize_game_record

game = generate_game(GeneratorConfig(seed=42))
session = GameSession(game.compiled_ruleset)

session.submit(session.legal_actions()[0])   # 走一步
print(session.history[0].action, session.history[0].player)
session.resign()                             # 当前行动方认输
print(session.result)                        # resignation, player 0 wins (...)

record = session.to_record()
text = serialize_game_record(record)
rebuilt = GameSession.replay(game.compiled_ruleset, deserialize_game_record(text))
```

要点：
* `submit(action)` 校验动作合法性（非法动作抛 Core 的 `IllegalActionError`），失败不会留下任何部分更新；会话已结束时提交抛 `SessionFinishedError`。
* `resign()` 只能由当前行动方调用；认输属于 Session 层，Core 的 `TerminalStatus` 不会被写入 resignation。
* `history` 是只读的 `tuple[ActionRecord, ...]`；每条记录包含 ply（从 1 起）、player、action、执行前后的稳定 position key。
* `GameRecord` 只保存重放所需最小信息（fingerprint + 动作序列 + 可选认输方），winner/终局结果一律通过重放重新推导。

### GameRecord JSON 格式

```json
{
  "schema_version": 1,
  "ruleset_fingerprint": "d8acd4028054f76bc294779cc04ea72d6f2ca98c97db4d608cb8423dd363f9d2",
  "actions": [
    {"kind": "board", "from": [1, 0], "to": [0, 3], "promotion_target_id": null},
    {"kind": "drop", "base_type_id": "P", "to": [3, 3]}
  ],
  "resigned_by": 1
}
```

序列化是规范 JSON（key 排序、紧凑分隔符、稳定输出）；反序列化严格校验字段类型（坐标为真整数，bool 不算；`schema_version` 只接受 1；`resigned_by` 只接受 0/1/null；未知字段一律拒绝），畸形输入统一抛 `SessionRecordError`，不会泄漏裸解析异常。
动作字段按 kind 严格区分：`board` 只接受 `kind/from/to/promotion_target_id`，`drop` 只接受 `kind/base_type_id/to`；混入另一类型字段（如 board 带 `base_type_id`）一律按未知字段拒绝。

## 安装与测试

```powershell
# 创建/激活虚拟环境（Python 3.11+）
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev]"

# 运行测试
.venv\Scripts\python.exe -m pytest -q

# 运行 headless demo（固定 seed，最多 50 ply，逐步校验系统不变量）
.venv\Scripts\python.exe -m generic_chess.demo.headless_demo
```

## 命令行双人对局与回放

```powershell
# 双人对局（默认 seed 42，8×8 classic_like）
.venv\Scripts\python.exe -m generic_chess.cli.play --seed 42

# 使用自定义 JSON RuleSet
.venv\Scripts\python.exe -m generic_chess.cli.play --ruleset examples/minimal_ruleset.json

# 保存对局记录（终局/认输/quit 时写入）
.venv\Scripts\python.exe -m generic_chess.cli.play --seed 42 --record-out game.json

# 同时保存本局实际 RuleSet 与对局记录，形成可独立回放的闭环
.venv\Scripts\python.exe -m generic_chess.cli.play --seed 42 --ruleset-out rules.json --record-out game.json

# 回放记录（必须显式提供 RuleSet 文件）
.venv\Scripts\python.exe -m generic_chess.cli.replay --ruleset rules.json --record game.json
.venv\Scripts\python.exe -m generic_chess.cli.replay --ruleset rules.json --record game.json --final-only
```

对局中可输入：合法动作编号（`1`）、与 `str(action)` 完全一致的动作串（如 `e2-e4`、`P@e4`）、`moves`、`board`、`history`、`help`、`resign`、`quit`。`--ruleset` 与 `--seed`/`--board-size`/`--preset`/`--hybrid` 同时给出时会明确报错（exit 2），不会静默忽略。`--ruleset-out` 在启动时写出本局实际 RuleSet（确定性、独立于对局进度），且不能与 `--record-out` 或 `--ruleset` 指向同一文件。棋盘以 `0:P` / `1:P` / `0:+G` 明确标识棋子阵营与升变状态（纯文本，不依赖颜色终端）。

## 棋子纹理生成（visual）

`generic_chess/visual` 是后续 UI 的底层基础设施：由棋子的真实 movement 结构程序化生成
确定性 SVG 纹理（而不是按 `type_id` 手工配图）。纹理反映走法几何——ray 走法带箭头、leap
走法圆头封端、中心格永远有显式标记；几何、配色、SVG 输出分层解耦，后续 Web UI / 预览 /
调试工具可以直接复用。

```python
from generic_chess.generation.config import GeneratorConfig
from generic_chess.generation.generator import generate_game
from generic_chess.visual import generate_piece_texture, PieceTextureStyle

compiled = generate_game(GeneratorConfig(seed=42)).compiled_ruleset
texture = generate_piece_texture(
    compiled.types_by_id["R"],  # 任意 PieceType
    owner=0,                    # 0=白方配色，1=黑方（几何旋转 180°），None=中性灰
    size=128,
)
print(texture.svg, texture.fingerprint)  # 同一输入输出完全稳定

custom = PieceTextureStyle(white_fill="#ffd700", center_marker_ratio=0.15)
texture = generate_piece_texture(compiled.types_by_id["P"], owner=1, style=custom)
```

生成示例/预览：

```powershell
# 经典类别（king/rook-ray/false-rook/bishop-ray/false-bishop/queen/pawn，双方配色）
# + 一个随机 RuleSet 的全部棋子类型；输出 SVG 与 index.html 预览页
.venv\Scripts\python.exe -m generic_chess.visual.preview --out visual_preview --seed 42
```

当前支持的视觉语义：正交/对角/斜向分支、ray 箭头、leap 圆头、八邻域 king（圆角方环 +
中心点）、单向 pawn（方向楔形）、正交+对角组合（queen 型）与随机复合棋子；中心格标记、
黑白/中性三套默认配色、描边、按 occupancy 归一化缩放。当前不做（架构上可扩展）：复杂阻挡
语义的细粒度视觉编码、move/capture 双图案全覆盖、promotion/drop 徽标、多层状态图标。

设计说明：走法几何而非名称驱动，保证随机规则也能得到稳定、可读、可区分的纹理；选择 SVG
是因为纯标准库即可生成、矢量缩放无损、可直接嵌入 Web；ray 与 leap 用箭头/圆头区分，避免
只靠长度；中心点标记棋子的原点与方向参考。

## 快速上手

```python
from generic_chess.generation.config import GeneratorConfig
from generic_chess.generation.generator import generate_game
from generic_chess.core.transition import initial_state, apply_action
from generic_chess.core.movegen import legal_actions
from generic_chess.rules.compiler import compile_ruleset
from generic_chess.rules.serialization import serialize_ruleset, deserialize_ruleset

# 1) 生成一套 8x8 classic_like 规则
game = generate_game(GeneratorConfig(seed=42))
compiled = game.compiled_ruleset
print(compiled.ruleset_fingerprint)

# 2) 从初始局面开始随机走棋
state = initial_state(compiled)
actions = legal_actions(state, compiled)
state = apply_action(state, actions[0], compiled)

# 3) 序列化往返（fingerprint 不变）
text = serialize_ruleset(game.ruleset)
compiled2 = compile_ruleset(deserialize_ruleset(text))
assert compiled2.ruleset_fingerprint == compiled.ruleset_fingerprint
```

### 公共 API（`generic_chess` 顶层导出）

| 函数 | 说明 |
| --- | --- |
| `compile_ruleset(rule_definition)` | 验证并编译 RuleSet（接受 RuleSet 或 JSON dict），返回 `CompiledRuleSet` |
| `initial_state(compiled)` | 初始 `GameState` |
| `legal_actions(state, compiled)` | 当前行动方全部合法动作（终局返回空列表） |
| `apply_action(state, action, compiled)` | 纯函数，返回新的 `GameState` |
| `pseudo_attacks(position, player, compiled)` | 伪攻击集合（frozenset[Square]） |
| `is_square_attacked(position, square, by_player, compiled)` | 单格攻击查询 |
| `is_in_check(position, player, compiled)` | check 判断 |
| `terminal_result(state, compiled)` | 终局状态（ongoing/checkmate/stalemate/repetition/max_ply） |
| `position_key(position, compiled)` | 稳定重复局面 key（SHA-256） |
| `generate_game(config)` | 生成 `GeneratedGame(ruleset, compiled_ruleset, generation_report)` |
| `serialize_ruleset(ruleset)` / `deserialize_ruleset(data)` | 规范 JSON 序列化往返 |

**严格合法性（v0 correctness hardening）**：`apply_action` 是唯一的公共落子入口，会先校验
`state` 与 `compiled` 的 fingerprint 一致，再校验动作确实存在于当前合法动作集合；任何伪造
动作（几何非法、越界、打入/升变不满足规则、自将）都会抛 `IllegalActionError`，状态/规则不
匹配抛 `RuleSetMismatchError`。机械执行函数是私有的 `_apply_action_unchecked`，不再从顶层
导出。所有公共查询入口（`legal_actions`、`pseudo_attacks`、`is_square_attacked`、
`is_in_check`、`terminal_result`、`position_key`）同样先做 fingerprint 匹配检查。

## RuleSet JSON 示例

完整、可直接编译的示例见 [`examples/minimal_ruleset.json`](examples/minimal_ruleset.json)
（4×4：anchor king + 可升变 pawn + 普通 gold，含全量 initial_position 与逐格 mask）。
下面仅展示结构片段：

```json
{
  "schema_version": 1,
  "board_size": 8,
  "piece_types": [
    {
      "type_id": "K",
      "name": "King",
      "movement_atoms": [
        {"kind": "leap", "offset": [1, 0]},
        {"kind": "leap", "offset": [0, 1]}
      ],
      "is_anchor": true,
      "is_promotable": false,
      "promotion_target_ids": []
    },
    {
      "type_id": "P",
      "name": "Pawn",
      "movement_atoms": [{"kind": "leap", "offset": [0, 1]}],
      "is_anchor": false,
      "is_promotable": true,
      "promotion_target_ids": ["G"]
    }
  ],
  "initial_position": [
    [{"owner": 0, "base_type_id": "P", "current_type_id": "P", "promoted": false}, null, null, null],
    [null, null, null, null]
  ],
  "drop_allowed": {"P": [[true, true, true, true], [true, true, true, true]]},
  "promotion_allowed": {"P": [[[0, 6, 0, 7]], [[0, 1, 0, 0]]]},
  "promotion_forced": {"P": [[[0, 7]], [[0, 0]]]},
  "repetition_limit": 4,
  "max_ply": 512,
  "stalemate_result": "draw",
  "metadata": {"seed": 42, "setup_preset": "classic_like"}
}
```

说明：
* 坐标统一为 `[file, rank]`，0-based；`initial_position` 按 rank 0（底）到 rank n-1（顶）排列。
* `drop_allowed` / `promotion_allowed` / `promotion_forced` 是逐格 mask（每个玩家一份），由 Generator 自动推导或手工指定；Compiler 不现场猜测。
* `metadata` 不参与 fingerprint，不会影响对局结果。
* fingerprint = SHA-256(规范 JSON：key 排序、排除 metadata、紧凑分隔符)，序列化往返后保持不变。
* 输入严格校验：`schema_version` 必须为 1；owner 必须是 0/1；布尔字段必须是真正的 JSON
  boolean（字符串 `"false"` 不会被当作 `True`）；所有畸形输入都会变成带 code/path 的
  `RuleValidationError`，绝不会静默纠正或抛裸 `KeyError`。

## 已实现规则（v0）

* 一般 n×n 棋盘（Core n ≥ 3；Generator 最小 4×4，因为每方默认 2n 枚初始棋子需要 4n 个空格），二人、完全信息、确定性、零和、交替行动、每回合一个动作。
* `LeapAtom`（跳，忽略中间格）与 `RayAtom`（滑行，按序到第一个占据格为止，`max_steps` 可选，方向要求 primitive vector）。
* 每方恰好一个 anchor（king 走法），anchor 不可捕获、不可打入、不可升变，不可进入被攻击格，两 anchor 不相邻。
* 捕获进持驹（恢复 base type，升变降格）、任意普通类型可打入、打入须空格且不导致自将、可打入将军/将死。
* 升变：逐格 promotion zone / forced mask；optional、forced、已升变不可再升变、结构性死亡 target 过滤、捕获后降格。
* 终局：checkmate、stalemate（和棋）、完整局面第 4 次重复和棋、512 ply 和棋。
* 序列化、fingerprint、固定 seed 复现、180° 旋转对称的双方规则。

## 明确留到后续（不在 v0）

* 图形 UI、网页、人机交互界面
* alpha-beta / heuristic / MCTS / 神经网络 / 训练逻辑
* 开局库、复杂性能优化（make/unmake 等）
* 二步（nifu）、打步诘（uchifuzume）、捕获式打入、anchor 打入
* 子力不足判和、50 回合规则、连续将军特殊规则（v0 一律按普通重复和棋）

第二阶段明确不做：heuristic evaluator、alpha-beta、MCTS、神经网络、Zobrist key、transposition table、move cache、make/unmake、图形/网页 UI、网络对战、计时器、悔棋、开局库、新棋规。Core v0 的规则语义保持不变。
第三阶段（visual）只提供纹理生成基础设施与预览工具，不做完整 Web UI，也不做 AI 搜索可视化。

## 测试

`tests/` 覆盖：坐标与 180° 旋转、leap/ray 语义、anchor 安全与自将、捕获与持驹、打入、升变、mate/stalemate、重复局面与 ply 上限、Generator 复现与过滤器、序列化与 fingerprint、旋转对称性、随机对局系统不变量（实体守恒、每方恰一 anchor 且在盘、无 anchor 捕获、同 seed 完全一致），以及 GameSession 行为、GameRecord 重放/严格校验、CLI 双人对局与回放 smoke 测试、纹理稳定性/阵营/类别区分/缩放/预览 smoke。

测试不使用 Hypothesis，全部使用固定 seed 的确定性断言。
