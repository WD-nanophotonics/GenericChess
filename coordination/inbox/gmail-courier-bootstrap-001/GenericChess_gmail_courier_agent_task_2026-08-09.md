# GenericChess：Gmail Courier 本地桥接程序实施任务

日期：2026-08-09

## 背景

GenericChess 现在采用 `master / sandbox / chat` 三工作区协作。Chat 负责上层规划与独立审计，Agent 主要在 `sandbox` 实施。当前 Chat 的 GitHub connector 可以读取仓库，但不能写 GitHub contents；另一方面，Chat 已实测可以通过 Gmail connector 创建/发送带附件邮件，并重新搜索、读取附件。

我们要建立一个**不让 LLM 参与信息搬运**的本地 courier。目的不是让 Agent 模型读取 ChatGPT 页面，而是让普通 Python 程序把 Chat 通过 Gmail 发出的任务/审计文件机械下载到本地 `chat/coordination/`，再用普通 Git 命令提交并推送 `chat`。这样 Agent 只在真正做工程工作时消耗 token。

## 第一阶段目标

在用户本地机器上实现一个很小、可靠、可后台轮询运行的 Python courier，先完成单向：

```text
ChatGPT
  → Gmail self-mail with attachments
  → local courier
  → GenericChess-chat/coordination/inbox/
  → git commit
  → git push origin chat
```

本阶段不要让任何 LLM、浏览器自动化或 ChatGPT UI 参与搬运。

## 当前 Gmail 协议

Chat 会把正式交付邮件发到用户自己的 Gmail：

```text
icywoods.1@gmail.com
```

正式消息使用 subject 前缀：

```text
[GC-BRIDGE]
```

建议区分：

```text
[GC-BRIDGE][TASK] <task-id>
[GC-BRIDGE][AUDIT] <task-id>
[GC-BRIDGE][CONTROL] <id>
```

邮件正文只做简短说明，**真正内容以附件为准**。常见附件：

```text
task.md
task.json
audit.md
audit.json
```

每个消息至少有一个稳定 `task_id`。如果 JSON manifest 存在，以 JSON 为机器协议权威。

## 本地环境与目标目录

GenericChess 三 worktree 约定：

```text
C:\Users\icywo\PycharmProjects\GenericChess          master
C:\Users\icywo\PycharmProjects\GenericChess-sandbox  sandbox
C:\Users\icywo\PycharmProjects\GenericChess-chat     chat
```

courier 的入站文件写入：

```text
C:\Users\icywo\PycharmProjects\GenericChess-chat\coordination\inbox\
```

程序自身不要污染产品目录；可以放在例如：

```text
C:\Users\icywo\PycharmProjects\GenericChess-tools\gmail_courier\
```

或者你判断更合适的独立本地工具目录。不要把 Gmail credential/token 提交到 GenericChess 仓库。

## Gmail 接入方式

使用**标准 Gmail API / OAuth 2.0**，不要通过 Selenium/Chrome 抓网页。

Agent 需要：

1. 给出最小权限 OAuth scope；优先只读 Gmail + 必要的 label/modify 能力，不申请发送权限，因为本阶段只下载 Chat 发来的消息。
2. 第一次运行允许用户在浏览器完成 Google OAuth 授权，之后使用本地 refresh token/token cache。
3. credential/token 文件必须在 Git ignore 范围，不进入任何仓库。
4. 搜索只处理发给用户自己的、subject 以 `[GC-BRIDGE]` 开头、带附件的邮件。
5. 不依赖 Gmail UI label 名称作为唯一状态；程序应有自己的本地 state database / manifest，确保幂等。

如果 Gmail API 的 exact scope / client setup 需要用户在 Google Cloud Console 创建 OAuth Desktop App，请把步骤写成非常短的 README，不要过度工程化。

## 必须满足的行为

### 1. 轮询

提供类似：

```powershell
python -m gmail_courier run
```

默认每 30 秒或 60 秒轮询一次，可配置。也应提供：

```powershell
python -m gmail_courier once
```

方便测试单轮同步。

### 2. 下载与目录结构

每封新消息建立独立目录，例如：

```text
coordination/inbox/<timestamp>_<message-id>/
    manifest.json
    task.md
    task.json
```

`manifest.json` 至少记录：

```json
{
  "gmail_message_id": "...",
  "thread_id": "...",
  "subject": "...",
  "received_at": "...",
  "attachments": ["task.md", "task.json"],
  "sha256": {"task.md": "..."},
  "processed_at": "..."
}
```

附件文件名必须 sanitize，防止 `../`、绝对路径或覆盖其他目录。

### 3. 幂等与原子性

这是硬要求：

- 同一个 Gmail message 重复轮询不能重复写入/重复 commit。
- 先下载到 temp 目录；附件全部成功并校验后再 atomic rename 到 inbox。
- 进程中途退出后重新运行必须安全恢复。
- 本地 state 至少持久记录 processed Gmail message IDs。
- 不允许因为一封坏邮件阻塞后续所有消息。

SQLite 或一个小型 JSON state file 都可以，由你根据可靠性选择；不要引入不必要的大依赖。

### 4. Git 集成

下载成功后，courier 自动在 `GenericChess-chat` worktree：

```text
git status --porcelain
git add coordination/inbox/<message-dir>
git commit -m "Receive Chat delivery <task-id-or-message-id>"
git push origin chat
```

约束：

- 只 stage 本次创建的 inbox 目录，禁止 `git add -A`。
- 如果 worktree 里存在与本次 courier 无关的未提交改动，不要覆盖或顺手提交；应记录 warning，并尽量只提交自己的新目录。
- push 失败时保留本地 commit/state，后续重试 push，不重复下载附件。
- 如果 Git branch 不是 `chat`，fail closed，不自动切换分支。
- 如果目录不是预期 Git repo/worktree，fail closed。

### 5. 日志

正常运行只输出短日志，例如：

```text
2026-08-09 22:30:00 no new deliveries
2026-08-09 22:31:00 received TASK native-semantic-executor-001
2026-08-09 22:31:01 committed abc1234
2026-08-09 22:31:03 pushed origin/chat
```

错误写清楚 message ID 和阶段，但不要打印 OAuth token、完整 credential 或敏感 header。

## 可选但推荐

如果很容易实现，可以加一个 Gmail label，例如：

```text
GC-BRIDGE/Processed
GC-BRIDGE/Error
```

作为人类 UI 提示。但**幂等权威仍应是本地 state**，不能只靠 label。

可以加一个 `--dry-run`，只搜索/列出将处理的邮件，不下载、不 commit。

## 不要做

本阶段不要：

- 调用任何 LLM API；
- 控制 Chrome/ChatGPT；
- 让 Agent 模型参与轮询；
- 自动执行附件里的 shell/python 指令；
- 自动把 `task.md` 交给 Codex 开始编程；
- 自动合并 `master`；
- 实现复杂 server/MCP；
- 把 OAuth credential 提交到 Git。

courier **只负责可靠传输，不负责理解或执行**。

## 测试要求

至少覆盖：

1. subject filter；
2. 无附件忽略；
3. filename sanitization / path traversal；
4. duplicate message 幂等；
5. partial download rollback；
6. hash manifest；
7. unrelated dirty worktree 不被 stage；
8. wrong branch fail closed；
9. commit failure / push failure 后安全重试；
10. mocked Gmail API 单元测试；
11. 一次真实 Gmail smoke test：从 `[GC-BRIDGE]` 邮件下载 Chat 发出的测试附件到 `coordination/inbox/`。

## 实施原则

这是一个小型基础设施工具。优先：

- 标准库 + Google 官方 Gmail API client；
- 结构清楚；
- 小依赖；
- 幂等；
- 可恢复；
- 日志可读；
- 不要为了“企业级”而加队列、数据库服务器、Docker、Web UI 等。

内部文件结构、class 名、是否 SQLite、CLI library 由你自己决定，不需要逐项请示。

## 完成回执

完成后报告：

1. 工具所在目录；
2. 安装/首次 OAuth 步骤；
3. CLI 用法；
4. 本地 state 设计；
5. Git integration 行为；
6. tests 结果；
7. real Gmail smoke test 结果；
8. 若需要用户手动创建 Google OAuth Desktop credential，明确只列出这一个剩余人工步骤。

如果真实 smoke test 需要本任务开始之后新收到一封 `[GC-BRIDGE]` 测试邮件，你可以先把程序准备好，再由用户让 Chat 发一封；不要用 LLM 或 Chrome 自动化替代 Gmail API。
