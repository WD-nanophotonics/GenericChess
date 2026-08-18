# GenericChess Native Semantic Executor — Dispatch 001

This is the formal Chat→Agent dispatch for the next GenericChess engineering phase.

## Current coordination state

- Treat the attached `GenericChess_native_semantic_execution_task_2026-08-09(1).md` as the full engineering specification.
- The authoritative product baseline named by that task remains master `3629c52b8c0bb4e92bd55851f2fc970d0407dadc`.
- Do not recover or reuse the discarded old Phase 1.9C-2 work.
- Current local prerequisite commits `a5fd94e` and `750c10a` are considered in-scope preliminary work if they are descendants of that baseline and contain only the reported payload/build safety changes. Do not discard them merely because the original task predates them.

## Immediate actions

1. Run the normal bridge/bootstrap preflight.
2. In the `sandbox` worktree, verify ancestry and working-tree cleanliness.
3. Push the current `sandbox` branch to `origin/sandbox` as early as practical so Chat can independently audit `a5fd94e` / `750c10a` while implementation continues.
4. Continue the attached Native Semantic Executor task autonomously. Do not wait for routine Chat approval between engineering steps.
5. Keep `semantic_position_state` and `semantic_s0_s4_executor` false until their stated acceptance conditions are actually satisfied.
6. When a meaningful reviewable checkpoint exists, push it to `origin/sandbox` and report the exact SHA through the established coordination channel.

## Collaboration rule

Chat audit and Agent implementation are intended to run in parallel. A formal PASS is required only for the exact candidate that is eventually promoted to `master`; intermediate sandbox development does not require approval gates.
