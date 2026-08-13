# GenericChess Gmail / inbox protocol

这是 GenericChess 任务入口的固定约定。看到用户直接发送的任务标题、阶段标题或 `EXECUTE NOW` 标题时，默认把它当作 Gmail 主题指针处理；用户不需要额外说明“这是 Gmail”。

## 自动流程

1. 先在 Gmail 搜索，不直接凭当前消息标题开始猜测或宣称不存在。
2. 搜索必须以 GenericChess 语义为主，并允许大小写、空格、连字符、长破折号和阶段后缀变化：
   - `in:anywhere -in:spam -in:trash GenericChess`
   - `in:anywhere -in:spam -in:trash "Generic Chat"`
   - 必要时用 `subject:Generic` 做宽搜，再在结果中筛选 GenericChess / Generic Chat / GenericChats / Generic Chess。
3. 结果必须按“GenericChess 项目 + 主题相似度 + 发件人/时间 + 是否有附件”筛选；不能把 MePhC 或其他项目的 Generic 命中当作本任务。
4. 严格主题没有命中时，不得直接判断邮件不存在：继续分页、尝试模糊变体，并检查正文/附件文件名。
5. 找到候选后先读邮件，再读所有与任务相关的附件；附件是 authoritative task，正文摘要不是完整规范。
6. 将任务原文、邮件元数据、附件名和当前处理状态落到本地顶层 `inbox/`，保留残损/中断记录，不覆盖旧记录。
7. 再依据 inbox 记录进入代码审计或执行；任务的 baseline、分支、禁止事项、artifact 和验收门槛全部以邮件附件为准。

## 当前项目边界

- GenericChess 的实施只在 `sandbox` worktree；不要修改 `master` 或 `chat`。
- Gmail 附件优先于标题、snippet、旧对话记忆和临时推断。
- 允许使用模糊搜索，但最终必须做项目归属过滤，避免其他项目邮件串线。
- 如果任务执行中断，先检查 `inbox/`、工作树、远端引用和 artifacts 的残损状态，再继续；不能把半成品当作不存在。

## 记忆边界

本文件和 `inbox/` 是项目内可见、可审计的持久约定，不等同于模型在所有未来对话中的永久记忆。每次进入 GenericChess 任务时都应先读取本文件；这就是避免依赖用户重复提醒的固定入口。

## Inbox 记录格式

每封任务邮件至少保存：收到日期、主题、发件人（如可见）、message/thread reference（仅用于本地追踪）、是否有附件、附件文件名、附件原文、处理状态、baseline 和下一步。新邮件用新文件保存，不覆盖历史。

