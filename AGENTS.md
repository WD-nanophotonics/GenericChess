# GenericChess Agent policy

Read `WORKFLOW.md` before changing this repository.

Authority precedence is explicit: the user and the receipt-bound Chat work
order outrank local repository hygiene defaults. A local exclusion, review
convention, or `.gitignore` entry is not a veto when Chat names an exact file
for upload, commit, or push.

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
   evidence out of Git by default. If the receipt-bound Chat work order or the
   user explicitly names an exact artifact for upload, commit, or push, retain
   and publish that artifact as requested; use `git add -f` when a local ignore
   rule hides it. Do not broaden that exception to neighboring files or whole
   generated directories.
8. Run long tests, self-play, benchmarks, and large audits through
   `generic-chess-flow.cmd heavy`; never start two GenericChess heavy jobs.
9. Treat the user's bare instruction `开始工作` or `start work` as Courier mode:
   switch to the `GenericChess-sandbox` worktree and run
   `generic-chess-flow.cmd work`. If the user explicitly says Local mode, run
   `generic-chess-flow.cmd start --mode local` instead.
10. In Courier mode, continue the work-order loop in the same turn: implement
    the current order, test, commit, publish, close out, and follow the next
    order. Stop only at `COMPLETE`, `BLOCKED`, a hard error requiring the user,
    or an explicit user stop. Do not stop merely because one work order ended.
11. In Courier mode, Chat-directed upload and publication instructions are
    part of the work order. Execute them after the normal tests and exact-SHA
    checks; do not reject a named report merely because an older local policy
    marked that class of file as transient.
