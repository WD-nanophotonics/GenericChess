# GenericChess v0 —— 通用棋类/将棋类引擎

一个确定性、无 UI 的通用棋类/将棋类游戏引擎，用于研究随机棋子走法、通用棋类 AI 与跨规则泛化。当前为第一阶段：Core Kernel（确定性规则内核）、RuleSet Schema 与 Compiler（声明/验证/编译）、Generator（带 seed 的规则与初始局面生成）、完整测试、序列化与无 UI 的命令行 smoke demo。

运行时仅依赖 Python 标准库（Python 3.11+）；`pytest` 仅为开发依赖。

## 三层架构

职责严格分离，未来的 UI 与 AI 只允许通过 Core 的公共接口访问合法性判断：

1. **Core Kernel**（`generic_chess/core/`）——只负责棋盘与状态表示、movement atom 语义、攻击判断、check、合法动作生成、捕获、持驹、打入、升变、状态转移、repetition 与终局。Core 内禁止任何随机数。
2. **RuleSet 与 Compiler**（`generic_chess/rules/`）——声明一套具体规则、严格验证、编译相对方向 / ray path / leap target / 升变区 / 打入 mask 为确定查询表，生成稳定的 SHA-256 fingerprint，并提供 JSON 序列化与反序列化。Compiler 只检查规则是否完备、自洽、可执行，不因“好不好玩”拒绝规则。
3. **Generator**（`generic_chess/generation/`）——软性偏好：棋盘大小、左右对称程度、ray/leap 比例、随机棋子走法、初始阵型、升变/打入规则推导、可玩性过滤、seed 复现。所有随机数只出现在 Generator，且使用局部 `random.Random(seed)`，不依赖模块级全局随机状态。

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
* `resign`（建议以后放在 GameSession 层）

## 测试

`tests/` 下 14 个测试文件覆盖：坐标与 180° 旋转、leap/ray 语义、anchor 安全与自将、捕获与持驹、打入、升变、mate/stalemate、重复局面与 ply 上限、Generator 复现与过滤器、序列化与 fingerprint、旋转对称性、随机对局系统不变量（实体守恒、每方恰一 anchor 且在盘、无 anchor 捕获、同 seed 完全一致）。

测试不使用 Hypothesis，全部使用固定 seed 的确定性断言。
