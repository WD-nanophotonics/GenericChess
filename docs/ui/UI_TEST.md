# UI Test 交接

本分支只为另一台电脑开发 UI 准备。引擎基线是
`b236c79ab7d11b2f234af4e099eb8b4208149f26`，分支名为 `ui-test`。
本机 `sandbox` 的后续研究独立推进；此处无需跟随研究进度。

## 已提供的完整运行链

- PySide6 桌面 UI、棋盘/持子/升变选择、规则查看、双方玩家设置。
- 棋局创建、内置国际象棋/将棋、既有生成器规则加载。
- 完整 GameSession 合法走棋、历史和终局处理、棋谱保存/重开。
- 安装版 AlphaBetaPlayer、标准棋类经验子力表、生成棋默认评价、预算分配、TT 和 q 搜索。
- 异步思考、进度回调、取消、过期结果丢弃、重新开局和窗口退出。

`generic_chess/ui/ai_backend.py:create_ui_player` 是固定玩家工厂。
新对局和重新开局均经此入口，显式使用 Python Core，不依赖可选的
原生库或另一台电脑的编译环境。棋力、速度和生成规则的趣味性不作保证；
AI 功能验收看实际合法 PVE 运行，不以胜率为标准。

研究 completion 前沿、小型学习评价器、未采纳的棋价/排序候选、未完成的
Native 优化不会接入此入口。仓库里保留的研究文档/历史归档是参考材料，
不是 UI 依赖或开发待办。矩形任意规则的默认棋价等尚不完整的能力也不作为
UI 必须支持的功能；先使用当前 UI 支持的内置或方形生成规则。

## 安装和操作

按根 README 的 clone、venv、`pip install -e ".[gui]" pytest` 和
`run_ui.py` 命令启动。不要复制本机 `.venv`、缓存或 `.local_agent`。
不需要 dev extras 中的 cshogi/Zig。C 扩展标为 optional，AI 工厂不使用它。
在“新对局”中选择 Human/AI；支持人类先手或后手。UI 调试建议固定思考
时间约 1 秒；不要用长搜索时间作为界面正常运行的前提。

## UI 与引擎边界

`UIController` 为 Qt-free 接口，UI 不直接更改 Position 或 GameState：

| 操作 | 现有入口 |
|---|---|
| 创建/加载 | `new_game`、`new_game_from_builtin`、`open_ruleset` |
| 设置双方/时间 | `start_match(MatchConfig)` |
| 显示 | `board_view_model`、持子/走法/结果 view models |
| 人类行动 | 控制器选择流程、`submit_action(Action)` |
| AI 是否行动 | `ai_move_needed` |
| GUI 线程捕获任务 | `capture_ai_search(CancellationToken)` |
| 工作线程搜索 | `player.choose_action(snapshot.session, snapshot.limits, cancel_token=token)` |
| GUI 线程提交 | `finish_ai_move(decision, snapshot)` |
| 停止/退出 | `cancel_ai`；等待工作线程结束后再销毁窗口 |
| 对局生命周期 | `undo`、`redo`、`restart`、`resign` |
| 棋谱 | `save_record`、`open_record` |

沿用 `MainWindow` 的 snapshot/generation 校验和取消流程，不把过期 AI
结果提交到新棋局。`PlayerDecision.action` 为实际公共 Action，对局提交
负责合法性/终局；UI 不复制走法规则、评价公式或搜索代码。

如果改为网页前端，可以在独立 UI 模块做薄服务适配器；本分支目前提供的是
桌面界面，不是假装已有 HTTP 服务。服务层保留真实 Action 序列化和完整
会话状态，HTTP/交互设计可以独立开发。

## 冻结与回归

`AI_BASELINE.json` 保存 UI 以外产品源码的 SHA-256（统一 LF 后计算，兼容不同电脑的 Git 换行设置）。开发者可改变 UI、
界面资源、启动器、UI 测试与薄接口适配器；不要修改搜索/规则/历史语义，
也不要更新清单来掩盖引擎修改。出现引擎问题，保留规则、棋谱、操作步骤，
交给 sandbox 处理，不让 UI 端变成第二条 AI 开发线。

`test_ui_test_pve.py` 使用真实 Core：国际象棋、将棋、普通/混合生成规则，
人类双方，实际轮换走棋、棋谱重开、重开/认输，以及真实 Qt 工作线程提交。
既有 UI 测试另覆盖取消、过期结果、退出和渲染生命周期。
这些有限用例验证交接链路，不意味着全部可能规则已无缺陷。

## 将来合并

UI 工作仅提交/推送 `ui-test`。不要定期合并正在研究的 sandbox，也不要
推送到 sandbox/master。完成后再做一次面向当前 sandbox 的 UI 合并：
保留当时 sandbox 的引擎与研究说明，选择 UI/资源/接口变化并跑 PVE 回归。
本分支专用 `AGENTS.md`、README、冻结清单与推送策略要人工协调，不能用
它们覆盖 sandbox 的研究政策。先不进行这次合并。

交接时验证：151 项 UI/PVE/生命周期/渲染测试通过；冻结清单中195个后端
源码文件与基线一致。后端没有为此分支修改，只有 UI 玩家工厂明确关闭原生
合法性加速。测试属于功能交接验收，不是棋力或所有规则无缺陷证明。

标准 Chess/Shogi 的用户授权子力表配置参见 [Web Material Score](WEB_UI.md#标准棋类的-material-score)，通过 UI 玩家工厂的公开配置接口接入；冻结源码及清单不变。
