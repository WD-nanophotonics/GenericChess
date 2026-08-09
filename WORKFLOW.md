# GenericChess 工作流

此 worktree 是 Agent 的开发 sandbox。所有未冻结的产品改动、调试和测试均在这里进行。

Chat 的计划和审计以 `chat` 分支中 `coordination/` 的已提交完整 SHA 交付。完成的产品候选只有在 Chat 审计绑定候选 SHA、约定测试通过且工作树干净时，才可由 Agent 晋级到 `master`。

`master` 只接收正式产品内容；协作材料不进入 `master`。
