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

桌面 UI（0.3.0，PySide6）：

```powershell
# 安装 UI 依赖（可选 extra：PySide6>=6.6,<7）
.venv\Scripts\python.exe -m pip install -e ".[gui]"

# 启动（默认 seed 42、8×8 classic_like；--smoke 用于无头自检）
.venv\Scripts\python.exe -m generic_chess.ui --seed 42
```

也可以安装 console script 后直接运行 `generic-chess-ui`。

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

## 桌面 UI（0.3.0，PySide6）

`generic_chess.ui` 是基于 PySide6 的可操作桌面棋类程序：`QMainWindow` + `QGraphicsView/Scene`
棋盘渲染、`QSplitter` 侧边栏（Piece / Game / History / Rules 四个标签页）、菜单/工具栏/状态栏、
`QSettings` 持久化。架构严格分层：Core/Rules/Generation → Session → **UI Controller** →
PySide6 View；视图不直接调用 `apply_action`，全部走子通过 Controller 的 `GameSession`
公共语义执行，绝不触碰 `_apply_action_unchecked`。Controller 是无 Qt 依赖的纯 Python
（设置存储抽象在 `ui/stores.py`，`QtSettingsStore` 作为 Qt 适配器在 View 层）。

视觉约定：**阵营色由 texture 的中心原点（center marker）颜色定义**——**owner 0 = 先手 =
白方**：白色中心原点 + 深色反差描边（外围主体为浅色）；**owner 1 = 后手 = 黑方**：黑色中心
原点 + 浅色反差描边（外围主体为深色）。棋盘默认 owner 0 在下方，Flip 只改变棋盘朝向，不改变
owner↔颜色映射。所有文案统一为 `White / Player 0 (先手)` / `Black / Player 1 (後手)`。

**持ち駒台（hand stand）**：棋盘上方固定显示后手台、下方固定显示先手台（随棋盘翻转跟随，
始终在“己方在下方”的一侧）。每个台子带边框，显示 texture + `type_id` + 数量；空手有明确
空状态。点击当前行动方的台子棋子进入 drop 模式（棋盘高亮合法落点），非行动方可看不可点；
右键/Esc 取消。

交互：

* **左键**：点击己方棋子选择并高亮真实合法着法；点击合法目标格走子；同一目标格存在多个
  promotion 动作时弹出升变对话框（每个选项显示升变后 texture 与 type_id，必要时含
  "No promotion"）。点击敌方棋子进入 **Movement preview**（蓝灰色、明确标注“不是合法着法”），
  preview 由只读 reachability adapter 基于 compiled movement 计算（ray 空格继续、敌方阻挡
  计入后停止、己方阻挡不计入并停止、结果去重），不做合法性与自将判断。
* **右键 / Esc**：取消选择、drop 状态与所有 overlay，不改变对局。
* **Drop**：点击持ち駒台中的当前行动方棋子进入 drop-selection，棋盘显示合法落点。
* **高亮**：selected（青蓝边框）、legal move（绿点）、legal capture（橙色圆环）、preview
  （蓝灰半透明）、last move（起点浅黄/终点橙黄）、check/threat（红边框）、hover（可关闭）。
* **Undo/Redo**：通过保留动作序列并 `GameSession.replay` 重建实现，只使用公开 API；
  历史列表双击进入只读历史局面，`Return to Current Position` 恢复。

文件操作：File 菜单支持 New Match…（统一开局：保留当前 / 生成 / 加载 RuleSet）、Open
RuleSet（严格反序列化）、Open Record（必须已有配套 RuleSet，fingerprint 校验）、
Save Record / Save As、Export RuleSet、Export Texture Gallery（复用 visual 模块）。错误通过
人类可读对话框展示，保留错误码，普通无效点击静默或仅提示状态栏；加载失败不会破坏当前对局。

Preferences（Ctrl+,）与 View 菜单共享同一状态源：View 菜单的勾选即真相，Preferences
修改会同步到菜单与 `QSettings`，重启后一致恢复；方向修改立即生效并持久化。持久化窗口几何、
splitter 位置、工具栏/侧边栏、棋盘方向、texture 占格比例、坐标/legal/last move/hover 开关、
敌方 preview 与唯一 promotion 自动选择等。

无头测试与自检：

```powershell
$env:QT_QPA_PLATFORM='offscreen'
.venv\Scripts\python.exe -m pytest tests/test_ui_controller.py tests/test_ui_app.py -q
.venv\Scripts\python.exe -m generic_chess.ui --seed 42 --smoke
```

## 通用 AlphaBeta Player（0.4.0）

`generic_chess.ai` 是适用于任意 GenericChess RuleSet 的通用 AlphaBeta 启发式玩家。它不依赖
传统棋种名称或固定子力表：棋子价值完全由 movement geometry、升变、drop、anchor/终局语义
自动推导，同一几何换任何 `type_id` 估值不变。设计细节见
[`docs/alphabeta_design.md`](docs/alphabeta_design.md)。

```python
from generic_chess.ai import AlphaBetaPlayer
from generic_chess.ai.limits import SearchLimits
from generic_chess.session.session import GameSession

session = GameSession(compiled)                 # 任意 RuleSet
player = AlphaBetaPlayer(compiled)              # 首次加载时构建并缓存评价 profile
decision = player.choose_action(
    session, SearchLimits(max_nodes=100_000, max_time_seconds=1.0)
)
print(decision.action, decision.score, decision.principal_variation,
      decision.nodes, decision.completed_depth, decision.termination_reason)
```

命令行分析 / benchmark / 自对局：

```powershell
# 输出某 RuleSet 的棋子价值 profile
.venv\Scripts\python.exe -m generic_chess.ai.cli.analyze_ruleset --seed 42
.venv\Scripts\python.exe -m generic_chess.ai.cli.analyze_ruleset --ruleset rules.json --json-out profile.json

# AlphaBeta 搜索 benchmark（node budget，可 --vs-random N 做与随机玩家的 smoke 对局）
.venv\Scripts\python.exe -m generic_chess.ai.cli.benchmark_alphabeta --seed 42 --nodes 100000 --repeat 5
.venv\Scripts\python.exe -m generic_chess.ai.cli.benchmark_alphabeta --seed 42 --nodes 20000 --vs-random 6
```

要点：静态 profile（mobility-density 曲线、movement graph、drop/promotion 分析）只构建一次并
进入版本化内存/磁盘缓存，搜索热路径只查表；TT 复用在同一 RuleSet 的连续着法之间，更换
RuleSet 自动以 fingerprint 隔离；预算支持 depth/nodes/time/cancellation；已加入 TT 与
保守 quiescence（捕获+升变），未加入 null-move/LMR 等高级剪枝。

## Human vs AlphaBeta 对弈（0.5.0）

桌面 UI 通过统一的 **New Match…**（Game 菜单 / 工具栏 / 侧边栏 “New” 均为同一入口）开始对局：

```powershell
# 启动 UI，Game 菜单 > New Match…
.venv\Scripts\python.exe -m generic_chess.ui --seed 42
```

`New Match…` 对话框可设置：

* **规则来源**：保留当前 RuleSet / 重新生成（preset + seed + 棋盘大小）/ 加载 RuleSet 文件；
* **双方玩家**：先手（White/Player 0）与后手（Black/Player 1）各自可选 **Human 或 AI**（可 AI vs AI 观战）；
* **时间控制**：无计时 / Byoyomi（读秒）/ Fischer（每手加秒），每方主时 + 加时/加秒；
* **AI 强度**：Auto（按剩余时钟时间分配，默认）/ Quick/Balanced/Deep 节点预算 / 固定每手秒数，可选最大深度。

**开新局永远从所选规则的初始局面开始**（不再从当前中途局面继续）。对局时：AI 思考在后台
线程执行（不阻塞界面），状态栏实时显示双方时钟与搜索进度
（`AI is thinking · depth 3 · 12,345 nodes`）；`Stop AI` 取消当前思考（再点一次恢复）；
**AI 思考期间时钟真实走动**，双方剩余时间清晰可见；**AI 超时判负**（状态栏标注
`AI timeout`，按 resignation 记录），**人类永不因超时判负**（时钟耗尽仅显示 00:00，对局
照常继续）；AI 会按剩余时间自动分配搜索预算（时间模式只设置 `max_time_seconds` 死线，无
固定 nodes/s 上限；每 128 个普通节点 + qnode 检查一次时间/取消，预算带安全余量），实际对局
中不会因“想太久”而超时判负，AI 超时判负仅作为极端情况兜底；Undo/Restart 与时钟联动
（Undo 恢复上一时刻时钟快照，Restart 后时钟从初始局面行动方重新计时）。
时钟是 Qt-free 的独立模块
（`generic_chess/clock.py`），AI 预算分配见 `generic_chess/ai/budget.py`。

终局说明：将死/和棋由 Core 的正式终局判定给出（将死时当前方合法动作数为 0），界面以
`Game over — <result>` 横幅与状态栏结果明确显示；在支持打入的规则里，“王无路可走但手牌
可以打援（例如打子挡将）”按规则**不是**将死，对局会继续——这是规则语义而非 bug。

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
| `legal_successors(state, compiled)` | 一次性返回全部 `(action, child_state)` 合法后继（搜索热路径用，避免逐子重复 movegen） |
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
第四阶段（0.3.0）提供 PySide6 桌面 UI：可玩棋盘、选择/合法着法/敌方 preview、drop、promotion、
undo/redo、RuleSet/Record 文件、Preferences 与状态持久化。仍不做：AI 搜索、MCTS 可视化、
联机对战、账号系统、完整 RuleSet 图形编辑器、Web 服务、大规模动画与音效。
第五阶段（0.4.0）提供通用 AlphaBeta heuristic player（规则派生棋子价值、mobility-density
曲线、两级静态缓存、TT、move ordering、保守 quiescence、benchmark/自对局 CLI）；仍不做：
null-move/LMR 等高级剪枝、MCTS/神经网络、Human vs AI 完整 UI 接入。
第六阶段（0.5.0）提供 Human vs AlphaBeta 桌面对弈：执白/执黑、Byoyomi/Fischer/无计时读秒、
AI 强度预设或每手秒数、后台搜索线程 + 实时进度 + Stop AI、超时按 resign 记录。

## 测试

`tests/` 覆盖：坐标与 180° 旋转、leap/ray 语义、anchor 安全与自将、捕获与持驹、打入、升变、mate/stalemate、重复局面与 ply 上限、Generator 复现与过滤器、序列化与 fingerprint、旋转对称性、随机对局系统不变量（实体守恒、每方恰一 anchor 且在盘、无 anchor 捕获、同 seed 完全一致），以及 GameSession 行为、GameRecord 重放/严格校验、CLI 双人对局与回放 smoke 测试、纹理稳定性/阵营/类别区分/缩放/预览 smoke、桌面 UI Controller 逻辑与 offscreen Qt 冒烟测试（启动、棋盘尺寸与翻转映射、texture 缓存、选择/走子/升变/undo-redo、文件与 Preferences），以及 AI 静态分析/价值/缓存/搜索正确性（minimax 等价、mate distance、预算/取消、TT 边界、repetition 隔离）。

测试不使用 Hypothesis，全部使用固定 seed 的确定性断言。
