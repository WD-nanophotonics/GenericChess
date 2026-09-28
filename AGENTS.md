# GenericChess local agent policy

This is the sole active policy for `GenericChess-sandbox`. The former Supervisor–Worker work-order workflow is archived under `docs/archive/courier_worker_20260928/` and has no authority. The latest user instruction takes precedence. Preserve unrelated work and historical evidence.

## One local agent

One local Codex agent owns research direction, implementation, tests, documentation, Git publication, and promotion. Do not wait for a Chat work order, Supervisor decision, transport ID, or SHA review before ordinary reversible work. Read `docs/research/LOCAL_MAINLINE.md` for the scientific route and `docs/operations/LOCAL_AGENT.md` for commands. Update the mainline document when evidence or a new user instruction changes the route. Keep any persistent objective short: read these documents, advance the mainline, verify work, and report actual blockers.

At the start of a research step, identify one unknown and the smallest direct observation that could resolve it. Prefer reasoning and bounded tests over large computation. Negative results that narrow the theory are useful; do not turn uncertainty into repeated bookkeeping or status-only turns. Long computation needs a resource limit and stopping condition; avoid concurrent Heavy jobs.

The agent decides whether and when to commit, push to `origin/sandbox`, and promote to `master`. Before publication, inspect the outgoing diff for personal or sensitive information and run relevant tests. Publish only cleared project work. Verify the remote SHA after a push. Promote only a tested, published sandbox commit by fast-forward when ready; never force-push or hide failing tests. A local commit does not imply publication. Report the actual state plainly.

## Chat is an adviser

On each active Asia/Tokyo weekday, send one sourced scientific consultation to the existing GenericChess ChatGPT Project through the reusable ChatCourier transport. Never send more than one new message on the same Tokyo date. Ask Chat to search world knowledge, papers, official rules, and relevant open-source projects, cite primary sources, challenge the local hypothesis, and offer bounded scientific suggestions. Chat does not issue work orders, approve publication or promotion, or decide the route. Its response is advisory evidence that the local agent evaluates. Do not send routine closeouts or status updates to Chat. If an earlier consultation is uncertain or pending, reconcile that same request before any new one; report a transport failure and continue independent research. Do not modify the separate ChatCourier repository as part of ordinary GenericChess work.

## Monitoring and stopping

The scheduled check runs every two hours and only detects whether local work is progressing or has a concrete problem. It also verifies this task's active Goal through the Goal tool when available; if unavailable, report Goal state as unknown rather than inferring it from files or activity age. It does not assign research, contact Chat, revive the old Worker, or create worktrees. Report a problem with evidence; healthy checks can stay quiet. Stop for an explicit user stop, whole-project completion, unavoidable user decision, or uncertain irreversible effect. Ordinary difficulty, a negative result, or absent Chat advice is not a stopping condition. If genuine user action is required, state the one action clearly in the final message rather than using tokens in a waiting loop.
