# GenericChess 工作流

此 worktree 是 Chat 的协作空间。Chat 只在 `coordination/` 中提交计划、审计、提示词和 artifacts，并用完整 commit SHA 交付给 Agent。

Chat 不修改产品代码；Agent 在 `sandbox` 中开发和验证。协作分工是约定，不使用角色权限、自动守卫或审批链。
