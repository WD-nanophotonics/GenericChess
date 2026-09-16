# GenericChess agent policy

This is the sole policy authority. `WORKFLOW.md` is only a command reference.
After context compression or a new work round, reread both files.

## Authority and repository

- Latest user instruction, the current registered Supervisor decision, this
  policy, the current Chat work order, then Worker judgment determine authority.
- Work only in `GenericChess-sandbox`; `master` changes only through an
  authorized fast-forward promotion.
- Preserve unrelated changes. Keep one registered Worker, writer, Courier
  browser, and Heavy job; never create a replacement request, worktree, or
  browser/profile.
- Generated binaries, raw benchmarks, Courier runtime, and transient evidence
  stay out of Git. Publish completed checkpoints to `origin/sandbox` and verify
  the full remote SHA.
- Never use Gmail, `gc-bridge`, a background Courier daemon, WSL, or a bypass
  transport.

## Worker loop

User's authoritative wording:

> “找chat要工单，回来完成工单，然后再发布，并汇报chat，chat给你工单，这是一个循环。”

In Courier mode, obtain the next order, implement it, test it, commit it,
publish it, close it out, and obtain the next order in the same turn. A phase
result, context compression, wait, or recoverable error is not a stop. Stop only
for an explicit whole-project terminal result, user stop, active Supervisor
HOLD, ownership conflict, uncertain irreversible effect, or severe harness
failure. Ordinary technical problems require two different reasonable attempts
before escalation.

A Chat `COMPLETE` closes the whole project only when the response explicitly
says no further GenericChess work is needed. A phase-level result continues to
the next work order.

Courier recovery is bounded: inspect the latest state, recover the existing
request, retry the same immutable request once when evidence permits, then
notify the Supervisor. Never create a replacement request. Transport faults
are not Chat `BLOCKED`.

## Compute and promotion

- Use `generic-chess-flow.cmd heavy` or `heavy-start` for long tests, self-play,
  benchmarks, and large audits. Never run two Heavy jobs.
- Every Heavy command declares a simple resource envelope. A scientific plan is
  optional supporting context for Supervisor judgment; Chat approval artifacts,
  plan/Sandbox/response SHA bindings, input-digest audits, and compute approval
  request/approve/revoke flows are obsolete and must not block Heavy.
- Keep one Heavy and the declared resource bounds. Prefer the cheapest
  sufficient experiment, small or split runs, and early stops. The Supervisor
  may authorize necessary mainline compute directly.
- The rolling 24-hour rule for work expected over two hours is a soft scheduling
  rule: when the rationale is weak or uncertain and another such run was
  recorded in the window, split the work or run useful small mainline work
  first. If no useful alternative exists and the compute remains necessary, do
  not leave the workflow idle; do not turn this rule into approval state or a
  hard block.
- Promotion is fail-closed: clean synchronized trees, successful required
  tests, an exact tested and published candidate SHA, explicit promotion
  approval, and fast-forward only.

## Safety and simplicity

Mechanical checks cover ownership, same-request Courier dedupe/recovery,
resource bounds, one Heavy, and tested/published state. Preserve real urgent
HOLDs and exact promotion binding; delete obsolete process gates. Do not add
a daemon, database, audit service, duplicate state store, new schema, or new
status category for a one-off incident. Process work expected to exceed
30 minutes needs a written recurring-loss justification and the smallest
sufficient fix.

Only the registered low-level Worker may use an enabled Goal. Do not touch
scientific production code while changing workflow infrastructure unless the
work order explicitly requires it.
