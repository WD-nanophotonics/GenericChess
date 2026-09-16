# GenericChess agent policy

This is the single authority file for the local workflow. `WORKFLOW.md` is a
command quick reference, not a second policy source. After context compression
or a new work round, reread this file instead of reconstructing rules from
memory or historical runtime records.

## Priorities and authority

Apply these priorities in order. A lower priority must never stop a higher one:

1. Keep the workflow running.
2. Advance playing strength, self-improvement, or a decision about the main algorithm.
3. Work efficiently and scientifically; avoid over-engineering and wasted compute.

Authority is: latest user instruction, this policy, current registered
Supervisor decision, current Chat work order, then Worker technical judgment.
History is evidence only and cannot overrule current registration or instruction.

The Supervisor may override Chat when Chat is blocking progress for formatting,
process, or other low-value reasons. Only genuinely uncertain irreversible
effects, an unresolved ownership conflict, or a problem outside granted local
authority requires the user. Any request for user intervention must explain:
(1) why no human-free solution exists, (2) why existing authorization and local
capabilities do not cover it, and (3) whether asking conflicts with the purpose
of an automated workflow.

## Repository and roles

- Work only in `GenericChess-sandbox`. `master` changes only through an
  authorized fast-forward promotion.
- There is one registered Worker, one Heavy job, and one Courier browser sender.
  Never create a second writer, worktree, browser/profile, or replacement request.
- Preserve unrelated changes. Publish completed code checkpoints to
  `origin/sandbox`; promotion requires the exact tested, published candidate SHA.
- Generated binaries, raw benchmark output, Courier runtime state, and temporary
  evidence stay out of Git. Commit concise reusable results only when they help a
  mainline decision.
- Keep project-scoped `approval_policy = "never"` and
  `sandbox_mode = "danger-full-access"`. Mechanical approval systems do not gain
  authority over the registered Supervisor.

## Continuous Worker loop

User's authoritative wording:

> “找chat要工单，回来完成工单，然后再发布，并汇报chat，chat给你工单，这是一个循环。”

The registered low-level Worker may use Goal mode and repeats that loop across
work orders. The Supervisor never uses Goal. A commit, closeout, phase result,
context compression, temporary lack of an order, Courier wait, or recoverable
error is not a stopping condition.

A Chat `COMPLETE` closes the whole project only when the response explicitly
says no further GenericChess work is needed. A phase-level result continues to
the next work order.

Stop only for an explicit whole-project terminal result, explicit user stop,
active Supervisor HOLD, ownership/second-writer conflict, uncertain irreversible
external effect, or a severe harness failure that may damage state. Ordinary
technical problems are escalated only after two different reasonable attempts
with no progress and no safe local option. New evidence or a new recovery stage
resets that count.

## Courier boundary

Courier is transport, not project management. It mechanically owns queueing,
sending, reply attribution, rate-limit/busy waiting, and same-request recovery.
It must not reject a useful response merely because ordinary control fields are
missing; defaults are `CONTINUE`, `NONE`, and `HOLD`.

Recovery is deliberately small:

1. If Chat is busy or rate-limited, wait and report that state to the Worker.
2. If the request is visible, do not send again; collect or wait for its reply.
3. If it is definitely unsent, send the same immutable request.
4. If send state is uncertain, one clearly labelled same-ID resend is allowed.
5. If ambiguity remains, notify the Supervisor and release unrelated queue work.

Never use Gmail, a background Courier daemon, WSL, another browser/profile, or a
new request to bypass recovery. Missing formatting is not a transport failure.
Only explicit controls may authorize whole-project `COMPLETE`/`BLOCKED`, compute,
or promotion.

Every Courier message reminds Chat to prioritize mainline scientific work.
Process or audit work must have indispensable reusable value; five consecutive
orders without mainline work is a direction warning, not a new hard gate.

## Compute and promotion

- Use `generic-chess-flow.cmd heavy` or `heavy-start` for long tests, self-play,
  benchmarks, and large audits. Never run two Heavy jobs.
- A Heavy run declares resource bounds. Large compute also needs a scientific
  plan and explicit Chat plus Supervisor approval for that plan.
- Approval binds the canonical plan, command, resource envelope, and explicit
  input digests. It does not bind unrelated repository HEAD changes or the
  storage hash of a Chat response.
- For expected work over two hours, prefer splitting it or running available
  smaller mainline work first. If no useful alternative exists and the approved
  computation is necessary, start it rather than leave the workflow idle. A
  prior large run inside 24 hours is a scheduling warning, not an absolute ban.
- Use the cheapest sufficient decision procedure and early stops. Do not run
  experiments whose result is already decided by existing evidence or algebra.
- Promotion remains fail-closed: exact candidate SHA, clean synchronized
  sandbox, successful required tests, explicit approval, and fast-forward only.

## Simplicity rule

Mechanical code checks only objective facts: exclusive ownership, whether a
request was sent, busy/rate-limit state, declared resource bounds, whether
inputs changed, and whether a candidate is published. Agents decide scientific
value, task priority, recovery usefulness, and whether continued work is sensible.

Do not add a daemon, database, audit workflow, duplicated state store, or new
status category to solve a one-off incident. Process/safety work likely to take
over 30 minutes needs a concrete recurring loss it prevents and must use the
smallest solution. Prefer deleting obsolete branches and tests over preserving
them indefinitely.
