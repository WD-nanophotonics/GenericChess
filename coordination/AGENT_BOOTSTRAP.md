# Chat coordination bootstrap

Before consuming Chat coordination artifacts, run `gc-bridge ensure` followed by
`gc-bridge sync`, update the chat worktree if appropriate, then read new
`coordination/inbox/` units. Do not use an LLM to manually poll Gmail when the
bridge is available.
