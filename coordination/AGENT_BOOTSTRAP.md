# Chat coordination bootstrap

Before consuming Chat coordination artifacts, run `gc-bridge ensure` followed by
`gc-bridge sync`, update the chat worktree if appropriate, then read new
`coordination/inbox/` units. Read and follow `coordination/AGENT_EXECUTION_POLICY.md`
for active tasks. Do not use an LLM to manually poll Gmail when the bridge is available.
