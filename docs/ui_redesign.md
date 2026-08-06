# GenericChess Desktop UI Redesign

本阶段重构桌面端的信息架构与交互稳定性，不改变 Core/Session/AI/native 语义。版本保持
`0.7.0a1`，本地 commit，等待真人视觉验收后决定 push 与版本号。

## 布局

```
菜单栏（文件 / 对局 / 查看 / 工具 / 帮助）
紧凑工具栏（新建 打开 保存 | 撤销 重做 | 翻转）
┌────────────────────────────────┬──────────────┐
│ 后手/黑方玩家栏（名称·状态·时钟·持驹）│              │
│            棋盘                 │  棋谱 | 规则  │
│ 先手/白方玩家栏                │              │
└────────────────────────────────┴──────────────┘
状态栏（左侧状态 + 右侧时钟）
```

棋盘为视觉主体（splitter 默认约 68/32，可拖动，主刷新不改变 splitter 比例）。

## 棋盘稳定性（P0）

`BoardView` 手动维护 `base_scale × user_zoom`：普通 `refresh()` 完全不触碰 transform；
仅 resize、board size 变化、orientation、fit 时重算 fit。滚轮默认无效；`查看 → 启用缩放模式`
开启后 Ctrl+滚轮 / +/- 缩放、超过 fit 时出现滚动条，`适应窗口`/Escape 回到标准状态。

## 侧栏

只有 **棋谱（Moves）** 与 **规则（Rules）** 两个页签：

* Moves = 原 Game + History：状态摘要（轮到谁 / AI 思考中 / 终局结果）、棋谱列表（每 ply
  人类可读记法）、回放控制（最前/上一手/返回当前/下一手/最后）；live/displayed ply 分离，
  回放状态禁止提交新着；终局不再显示 “to move”。
* Rules = 原 Piece + Rules：RuleSet 概要（棋盘/类型数/打入/升变/重复/胜利条件，无
  fingerprint/seed）、棋子类型列表（真实 texture）、详情（纹理、anchor/升变/打入、结构化
  本地化走法描述、可折叠技术表）、实体棋子信息条；棋盘/持驹/列表均可 inspect。

## 玩家栏与持驹

`PlayerBar` 取代上下大块 hand container：名称、先手/后手、行动指示、时钟、紧凑可点击持驹
（`[A ×2]`，空手显示“无”）；点击持驹进入 drop 选择（再次点击/Esc 取消），右键 inspect 类型；
Flip 只交换上下栏视觉位置，owner 语义不变。

## 本地化

`generic_chess/ui/i18n/`：`manager.py`（Qt-free，`text(key, **values)`、语言持久化、即时
刷新）+ `en.json` / `zh_CN.json` / `ja_JP.json`。菜单、工具栏 tooltip、页签、玩家栏、状态栏、
Moves、Rules 概要/走法描述、Preferences、Diagnostics 均走统一翻译层；走法描述由
方向/模式/距离/阻挡结构化 token 组合。

## Diagnostics

工具 → 诊断信息：应用版本、fingerprint、seed、规则/棋谱文件、position key、ply、后端、
native available/version、Python/Qt 版本，含复制按钮。普通主界面不再显示这些字段
（Preferences → 高级可开启“状态栏显示开发者信息”，默认关闭）。

## 保留项

Human vs AI、AI 取消/世代守卫、时间控制、安全关闭线程、New Match/Restart、文件对话框取消
语义、native 模块与测试均未改动。
