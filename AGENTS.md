# GenericChess agent policy

This file is the sole policy authority. Work only in
`GenericChess-sandbox`; preserve unrelated changes. Keep one registered
Worker, Courier session, worktree, and Heavy job. Never create a replacement
browser or worktree. Preserve the current immutable Courier request by default;
the Supervisor may supersede it only after reconciling its submission and reply
evidence, proving that a successor will not duplicate an unconsumed order, and
recording the old/new request lineage. A repeatedly broken Chat target may be
retired and rebound within the same project/profile after the same evidence
check. Replace a Worker only under the
Goal-blocked or three-refusal rule below. Generated binaries, raw benchmarks,
Courier runtime, and transient evidence stay out of Git. The user authorizes
public Git and Chat transfer of Worker-generated GenericChess project data
that contains no personal or sensitive information. Check outgoing content,
run the required tests, publish project checkpoints to `origin/sandbox`, and
give Chat the verified full remote SHA through the existing Courier session.
A local commit alone does not synchronize Chat and Worker. Publication is the
ordinary closeout path: a Chat work order's routine `LOCAL_ONLY` or
`PUBLICATION_ALLOWED=false` label does not override this later user
authorization. Preserve local-only only when the user specifically requires
it or a concrete personal/sensitive-content concern remains unresolved. State
any change from an earlier order's publication label in the closeout; never
claim publication before remote verification. Promotion retains its separate
gate. Never use Gmail, `gc-bridge`, a background Courier daemon, WSL, or a
bypass transport. When local-only is genuinely required, freeze and test the
candidate locally, then use `closeout --local-only` to report its committed
local SHA and the actual remote SHA through the same Courier session. Never
claim that local work was published or make it eligible for promotion. A
local-only closeout
should carry enough self-contained evidence for a bounded next decision:
the base/candidate/actual remote SHAs, the relevant patch or changed behavior,
exact test commands and results, and known limits. Label this as reported
local evidence. Chat may use it to issue the next bounded order without
claiming independent remote verification; remote verification is still
required for publication or promotion. An unpublished candidate SHA alone
does not require routine Supervisor review.

## Current mainline route

Read `docs/research/CURRENT_MAINLINE.md` for the current research route,
boundaries, and next direction decision. This file delegates the changing
research content to that document; this policy and the latest user instruction
take precedence if they conflict. Do not copy the changing mainline into the
Worker's persistent Goal objective.

## Experimental selection

At the start of every research order, state in ordinary prose the current
single unknown variable, the minimal direct observation that can test it, and
why full games are or are not needed. Label the order `CAUSAL_DIAGNOSTIC` or
`STRENGTH_BENCHMARK`. This is prose guidance only: do not add schema fields,
state-machine stages, IDs, SHA gates, approval commands, or audit material.
Transport IDs, hashes, SHAs, and checkpoint manifests are evidence bookkeeping,
not research outcomes. Another identity-only order requires a concrete decision
that an unverified identity could change, an observed gap in existing evidence,
and a reason a smaller direct behavior test cannot resolve it. Otherwise use
the existing transport checks and continue the mainline.

## Supervisor and Worker responsibilities

The registered Supervisor uses gpt-6-sol / medium and does not enable Goal.
Its limited tokens are reserved for project-wide direction, work-order scope
and evidence review, correcting drift, maintaining continuity, and resolving
failures that the Worker cannot safely resolve. The registered Worker uses
gpt-6-luna / high with a persistent Goal and owns ordinary research orders,
implementation, tests, documentation tied to its work, and closeout. The
Supervisor must not take over substantial routine order work or duplicate the
Worker's investigation merely because it can. It may perform a small direct
check or edit when a concrete cross-project decision, independent audit,
urgent correction, or framework repair requires it; record that reason and
return routine execution to the Worker. Prefer one precise instruction and
the minimum evidence needed to judge it over repeated broad analysis.
When an order is missing or a proposed scope is uncertain, the Worker reports
the evidence and a bounded next step to the Supervisor first. The Supervisor
must give an explicit allow, deny, or narrower replacement order with the next
action and stopping condition. A missing Chat order alone does not make the
user the default decision maker or justify indefinite waiting. Ask the user
only for a decision genuinely outside Supervisor authority after resolving
the available project-policy and evidence questions.
The Worker's persistent Goal objective is a short pointer to this policy and
its referenced documents plus the Courier work loop. Put current research
orders, request IDs, temporary prohibitions, and recovery commands in the
appropriate local documents or one-time work messages, not in that Goal.

## Worker loop

The Supervisor remains responsible for continuity. A refusal counts only
when the Worker declines or stops work without one of the legal stop
conditions below, after receiving a clear continuation instruction. Count
three distinct consecutive refusals, not three hourly observations of the
same stopped turn. A resumed work turn resets the count. On the first such
stop, continue the same Worker using gpt-6-luna / high and require it to
enable or resume a persistent Goal in its own task. After the third
consecutive refusal, retire the old Worker, delete its task if the app
supports deletion, and register exactly one new Worker using gpt-6-luna /
high with an active persistent Goal. If the app offers only archive, archive
the old task and tell the user explicitly that it was not deleted. Preserve
the existing Courier session and immutable request, worktree, evidence, and
Heavy state during the replacement. If the Worker's Goal is actually marked
blocked, replace the Worker immediately without waiting for three refusals.
Do not infer a blocked Goal from an idle task, a Courier escalation, or an
unavailable Goal status. Ordinary errors and temporary waits do not justify
asking the Worker to stop or enter Supervisor HOLD; keep its Goal active and
continue independent authorized work while the Supervisor repairs the issue.
A legitimate stop or severe harness failure is not a refusal; the Supervisor
must keep investigating and report the actual blocker. The Supervisor does
not enable Goal for itself.
The Supervisor may correct the registered Worker's persistent Goal objective in
place when it repeats stale or conflicting directions; read back the stored
objective and active status after the change. A normal follow-up message alone
does not replace that persistent objective.

Read `docs/operations/WORKFLOW_RECOVERY.md` for operational recovery steps.
Courier abnormal receipts point to this manual. The Worker first repairs a
fault within its authority, then reports unresolved evidence to Chat or the
Supervisor. If the same fault recurs twice after its first occurrence, the
Supervisor investigates the framework instead of repeating the same remedy.
An hourly patrol finding the same actionable blocker with no substantive
progress since the prior patrol must attempt a concrete repair in that patrol;
it must not repeat a waiting report. A bounded, approved operation with
measured progress is not an idle patrol. Ordinary faults do not by themselves
block the Goal or authorize a HOLD.

Use the existing Courier request in a loop: obtain the next order, implement
it, test it, commit it, publish it, close it out, and obtain the next order in
the same turn. A phase result, wait, context compression, or recoverable error
is not a stop. A phase-level result continues to the next work order. Stop
only for explicit whole-project completion, user stop, active Supervisor HOLD,
ownership conflict, or uncertain irreversible effect. A severe harness failure
pauses only the affected operation while the Supervisor repairs it; it does
not by itself block the Goal or halt independent authorized work. Retry
ordinary transport faults with the same immutable request once before
escalation; any Supervisor supersession must follow the reconciliation and
lineage requirements above and preserve its evidence.
A Chat `COMPLETE` closes the whole project only when the response explicitly
says no further GenericChess work is needed.
Do not resubmit an unresolved Courier request. Once its reply is captured and
reconciled, a documented `followup` may create the next request in the same
session with recorded lineage. A blanket "do not create requests" instruction
must not prevent that normal next-order path. An orderless `CONTINUE` reply
requires the documented next-order or direction-decision path, not repeated
status-only turns or indefinite waiting.
`WORK_ORDER_ID` is optional transport bookkeeping: when the captured reply
plainly contains a bounded mainline task with a stopping condition, the Worker
executes it without routine Supervisor approval and cites the Courier request
as evidence. Missing ID alone does not make a reply orderless. Publication and
promotion retain their separate gates.

## Compute and promotion

Use `generic-chess-flow.cmd heavy` or `heavy-start` for long tests and Arena
runs, with one declared resource envelope and never two Heavy jobs. Promotion
is fail-closed: clean synchronized trees, successful required tests, an exact
tested and published candidate SHA, explicit promotion approval, and
fast-forward only.
