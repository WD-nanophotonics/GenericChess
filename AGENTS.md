# GenericChess Agent policy

Read `WORKFLOW.md` before changing this repository.

1. Work only in the `sandbox` worktree. Treat `master` as immutable except when
   `generic-chess-flow.cmd promote` performs an authorized fast-forward.
2. Start every task in either `courier` or `local` mode. Never silently switch
   authority modes during an active task.
3. Preserve unrelated user changes. A completed checkpoint must be tested,
   committed, published to `origin/sandbox`, and verified by full SHA.
4. In Courier mode, follow the receipt-bound Chat work order without expanding
   its scope. Report only pushed SHAs. Promotion requires Chat approval bound to
   the exact candidate SHA.
5. In local mode, do not invoke Courier. The local Agent owns technical
   decisions below explicit user instructions and may authorize promotion after
   the documented gates pass.
6. Never use Gmail, the retired `gc-bridge`, a background courier daemon, WSL,
   a second browser/profile, or a replacement request to bypass ChatCourier.
7. Keep generated binaries, Courier state, raw benchmark output, and transient
   evidence out of Git. Retain durable architecture decisions as ADRs and
   behavior guarantees as tests.
8. Run long tests, self-play, benchmarks, and large audits through
   `generic-chess-flow.cmd heavy`; never start two GenericChess heavy jobs.
9. Treat the user's bare instruction `开始工作` or `start work` as Courier mode:
   switch to the `GenericChess-sandbox` worktree and run
   `generic-chess-flow.cmd work`. If the user explicitly says Local mode, run
   `generic-chess-flow.cmd start --mode local` instead.
10. In Courier mode, `CONTINUE` is a mandatory continuation invariant. Implement
    the current order, test, commit, publish, close out, and immediately follow
    the next order in the same task. A closeout, checkpoint, successful push,
    phase completion, queue wait, or one finished work order is never task
    completion. While `CONTINUE` or a next `WORK_ORDER_ID` is present, do not
    send a final response, call `finish`, wait for the user, or create a
    replacement request.
11. Stop only at an exact `COMPLETE`, a genuine `BLOCKED` requiring user or
    external action, a hard error requiring the user, or an explicit user stop.
    Before any final response, verify that no active work order remains, the
    latest control footer is terminal, the request is reconciled, and the
    latest checkpoint SHA was pushed and verified. Never reinterpret an
    unfinished safe task as blocked or complete.
