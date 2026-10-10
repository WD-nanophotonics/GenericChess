# 弈境 · GenericChess 网页小游戏

UI-only local browser game on `ui-test`. The Python engine remains frozen at the
baseline in `AI_BASELINE.json`. No Courier, Qt, research state or native tooling
is needed for the Web service. The existing desktop UI is retained.

## 在这台 Windows 电脑上运行

双击仓库根目录 `run_web.bat`，或运行：

```powershell
.web-venv\Scripts\python.exe run_web.py
```

服务仅监听 `http://127.0.0.1:8765`，就绪后打开浏览器；Ctrl+C 停止并取消 AI。
`--no-browser` 不自动打开网页，`--port 8766` 改用其他端口。
默认从 `.web_state/` 原子保存/恢复；`--state-dir <directory>` 可使用独立存档。
重复启动会识别同一工作区和存档目录的已有游戏服务，直接打开页面。
其他服务、不同工作区或不同存档占用端口时，仍提示改用其他端口。
启动器检查端口和前端构建。新目录应先完成下方安装，不能只复制启动器。

## 从干净克隆安装

Windows / Python 3.11+；前端构建使用 Node 22.12+（本机验证：Python 3.12.0、
Node 22.15.0、React 19、Vite 7）。运行已构建版本时不需要 Node。

```powershell
python -m venv .web-venv
.web-venv\Scripts\python.exe -m pip install -r web/requirements.lock -e ".[web]"
cd web
npm ci
npm run build
cd ..
.web-venv\Scripts\python.exe run_web.py
```

`.web-venv` 专供网页环境，无 PySide6；`.venv` 可继续用于桌面 UI。
Node 依赖由 `web/package-lock.json` 锁定，Web Python 运行依赖由
`web/requirements.lock` 锁定。`web/dist` 不提交 Git，切换代码后按需重新构建。

开发时，在两个终端分别启动 Python 服务及 `web` 目录的 `npm run dev`。
Vite 的 `/api` 代理连接本机 8765 端口，开发网页为 `http://127.0.0.1:5173`。

## 对局与存档

- 首页选择生成棋、混合生成棋、国际象棋或将棋；人机支持玩家先/后手，也可同屏双人。
- 默认生成棋 8×8、seed 42、玩家先手、AI 固定 1 秒。没有对局倒计时。
- 点击或触摸棋子后点击合法目标；打入先选择持子。多个合法行动会展示升变/语义选项。
- 任意棋子可查看手册。箭头键移动棋盘焦点，Enter/Space 选择，Escape 取消选择。
- 人机悔棋回到玩家上次决策前；双人悔棋撤回一步。玩家尚未行动时不能撤回 AI 首步。
- 回看棋谱暂停搜索，返回当前局面后继续；“暂停 AI”可手动控制。错误时保留棋局并允许重试。
- 冻结引擎只允许当前行动方认输，因此 PVE 的认输按钮仅在玩家回合开放。
- 每次持久状态变更自动保存规则、棋谱、玩家配置及 AI 暂停状态；重启后在首页选择继续。
- 菜单可导出原生棋谱、规则或完整续局包。随机棋谱导入须先加载匹配规则；续局包包含全部规则。
- 导入在独立控制器上验证/replay，失败保留当前对局；文件内容上传，不接受本机路径。
- 存档写入失败会明确提示，仍可导出续局包。损坏存档保留，首页报告读取失败。
- 断线自动重连并获取完整状态；不自动重发未确认操作。停止服务前建议保留重要棋局的续局包。

## 验证与诊断

完整桌面/Web 测试环境：

```powershell
.venv\Scripts\python.exe -m pip install -e ".[gui,web]" pytest httpx
.venv\Scripts\python.exe -m pytest -p no:cacheprovider tests/product/test_web_ui.py
```

原有桌面 UI/纹理回归仍按 `tests/product/test_ui_*.py`、`test_textures.py` 和
`test_texture_preview.py` 运行；`test_ui_test_pve.py` 同时检查 195 个冻结后端文件。

启动本机服务后，在 `web` 目录运行 `npm run test:e2e`；测试使用已安装的
Microsoft Edge，无需下载测试浏览器。桌面和 390×844 触摸视口各覆盖完整 PVE、
导入导出、悔棋、终局、离线恢复、键盘及升变/打入。

运行 `node scripts/measure_web_ui.mjs` 测量选中反馈、AI 搜索期间状态/取消延迟。
原始数据及截图存至忽略目录 `artifacts/web-ui/`，不是产品运行依赖。
初次验收：170 项桌面/纹理、24 项 Web API 和 16 项浏览器用例通过；
195 文件冻结校验一致，干净 Web-only 安装无需 Qt。

2026-10-10 本机 Edge headless、1366×1000、AI 1 秒预算的测量：
32 次选中反馈 p95 20.3 ms / 最大 50.7 ms；40 次状态读取 p95 52.1 ms /
最大 71.9 ms；4 次取消最大 69.3 ms。均低于 100 ms / 500 ms 目标。
这是有限本机样本，不是所有生成规则、机器或浏览器的性能保证。

首版限制：本机浏览器，同屏对局；单个共享 AI 线程按顺序搜索，不用于公网多用户。
前端支持窄屏布局，但当前服务不开放手机局域网访问。界面以中文为主，规则 ID
保留原始标识。AI 不保证棋力，异常规则问题交给 sandbox，不修改冻结后端。
