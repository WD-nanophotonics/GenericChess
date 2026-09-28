# GenericChess workflow recovery manual

This is an operational runbook under `AGENTS.md`, not a second policy source.
Use the current project policy and the latest user instruction if they differ
from a procedure here. `WORKFLOW.md` lists ordinary commands. Keep one Worker,
Courier session, worktree, and Heavy job. Do not turn an ordinary error into a
Supervisor HOLD or a blocked Goal.

## Supervisor attention budget

The ordinary work path is Chat -> existing Courier request/session -> Worker:
Chat supplies research orders, and the Worker implements, tests, closes out,
and obtains the next order. The Supervisor is not a standing order source or
the Worker's routine research partner. Do not turn a healthy Worker checkpoint
or a missing next Chat order into a recurring Supervisor-assigned investigation.
Supervisor contact is for a concrete policy decision, independent audit,
material scope drift, or a fault the Worker cannot safely repair.
The Worker's Goal objective is persisted and reintroduced across turns. When
its text is stale, inspect the registered task's actual Goal, update that same
thread's objective through Codex `thread/goal/set` while retaining `active`,
then use `thread/goal/get` to verify the stored text and status. Do not treat a
follow-up prompt or an edit to this manual as proof that the old Goal vanished;
do not edit the Goal SQLite database directly or replace a healthy Worker for
this purpose.
Do not make Supervisor final review a blanket field on ordinary work orders.
Chat and the Worker should complete routine, reversible, bounded changes using
their normal tests and Courier closeout. Request Supervisor review when a
specific risk warrants an independent decision: an irreversible or promotion
step, uncertain publication/lineage, substantial scope or resource expansion,
conflicting policy or evidence, or a shared workflow failure. Name that risk
in the order or escalation. Honor an already issued order's explicit review
requirement; ask Chat through Courier to narrow the requirement for future
routine orders rather than silently disregarding it.

Use Supervisor turns to set direction and bounds, review decisive evidence,
correct Worker drift, and repair shared workflow failures. Delegate routine
RuleSet, research, code, test, and closeout work to the registered Worker.
Before doing order-sized work directly, identify the concrete reason the
Worker cannot do it or why an independent Supervisor check is essential;
keep that intervention bounded and hand execution back. For an ordinary
healthy Worker turn, inspect only the evidence needed for the next decision
and avoid reproducing its entire analysis or test run. A short independent
check remains appropriate when it resolves a material uncertainty about a
checkpoint or prevents an incorrect project-wide decision.
When Chat has no usable next order, first reconcile the same Courier request
and use its documented safe recovery path; do not bypass Courier by directly
messaging Chat. The Worker may continue only already authorized independent
work. If the order path remains unusable, the Worker sends the Supervisor the
request/reply evidence, the recovery tried, and one bounded action with its
stop condition. The Supervisor repairs the order path where possible and
otherwise explicitly allows, denies, or narrows that temporary action. The
decision is a bridge across the specific gap, not a standing stream of new
Supervisor work orders. Return order ownership to Chat as soon as the existing
Courier path can supply a usable order. Do not forward a routine scope choice
to the user or keep requesting new tests while no project question is settled.

## Mainline stop-loss

The Supervisor may cut short an order or recovery route that is visibly
consuming work without advancing the current AGENTS.md mainline. One strong
trigger is that the last ten distinct exchanges with the Worker contain no
direct mainline result or test of a mainline uncertainty. Count exchanges,
not hourly patrols or repeated status messages. Ten is an evidence threshold,
not a mandatory waiting period: a clear earlier diversion may also warrant
action. Conversely, recent substantive RuleSet work means this particular
ten-exchange trigger has not fired even if Courier itself is troublesome.
Repeated ID, source-hash, SHA, provenance, or refreeze orders count as a detour
when they do not settle a concrete mainline decision. Keep Courier's immutable
request, reply matching, and publication/promotion SHA checks; those are
mechanical safeguards. Before allowing further identity research, identify
the exact wrong decision it prevents and compare its cost with the smallest
direct behavioral test. If that case is absent, decline the next identity-only
scope through the existing Courier reply path and request a mainline order.

Before acting, identify the current mainline, the concrete detour, the cost
of continuing it, and the smallest reversible stop-loss action. The Supervisor
may deny a proposed route, end a low-value order, or retire and rebind a
repeatedly unusable Chat target within the same project/profile when doing so
helps the mainline and has limited workflow cost. Tell the Worker exactly
which work stops, what authorized work continues, and the next decision point;
do not describe an ordinary course correction as a blocked Goal or impose a
HOLD by default. Preserve committed work, tests, request/response evidence,
and old/new lineage. Before replacing a Chat target or request, reconcile
submission and reply evidence and prove that no unconsumed order can be
duplicated. Keep the registered Worker, Courier session, worktree, and Heavy
constraints from AGENTS.md. Record the reason and result so a later patrol
does not resume the discarded detour.

## On every abnormal Courier receipt

1. Read the receipt, its `recovery_manual_path`, the current immutable request
   ID, the last event, and the safe next action. `ok: true` waiting events can
   still need follow-up. A busy Chat is temporary contention, not a project
   stop. Do independent authorized work while waiting.
2. The Worker tries the documented same-request recovery within its authority.
   For a transport fault, retry once with the same request, then inspect the
   exact request and reply evidence. Do not create another request, Chat,
   browser, transport, worktree, or Heavy job to get around uncertainty.
3. If the Worker cannot repair it, send Chat or the registered Supervisor the
   request ID, event/error fingerprint, receipt and diagnostic paths, actions
   already attempted, and what independent work remains possible. The Worker
   keeps its Goal active and continues that work.
4. Count occurrences of the same underlying error fingerprint, not every
   retry log line. At the first occurrence plus two recurrences, the Supervisor
   must inspect the framework path that emits the fault. Repeating an unchanged
   command or asking the user to choose without new evidence is not recovery.

## Hourly Supervisor patrol

Read `AGENTS.md` and `WORKFLOW.md`, then this manual. Inspect the registered
Worker task and actual Goal status, the same Courier session and request,
recent receipt and response evidence, Heavy status and measured progress,
active HOLD, both worktree SHAs and remote sync, and the latest substantive
research output. Do not infer `blocked` from idle, escalation, or missing Goal
data. Query the Worker or available state tools when evidence is missing.

Run `generic-chess-flow.cmd supervisor-patrol --issue-key <stable-fingerprint>
--progress-key <evidence-fingerprint> --worker-state <state> --goal-state
<active|blocked|unknown>`. Use `none` for no issue. The progress key must
represent verifiable changed work such as a new Worker turn containing work,
new result/commit, a newly captured response, or increased measured steps of
an approved Heavy. A new clock timestamp, repeated status sentence, or Heavy
heartbeat alone is not progress. The command compares this observation with
the prior patrol in ignored local runtime state. If it reports
`action_required`, perform a concrete recovery action, then call the command
again with identical observation fields and `--action <what-was-done>` to
record it. The command does not advance a stalled observation without an
action. Goal `blocked` requires immediate Worker replacement; the repeated
stalled issue rule requires immediate investigation and repair, not automatic
Worker replacement.

An approved Heavy within its hard envelope and with measured work increasing
is legitimate progress. If the envelope is exceeded or progress has ceased,
inspect and repair or stop that job under its existing controls. A Chat wait
does not halt independent Worker work. Send the user one short mobile-visible
patrol result with time, Worker/Goal, Heavy/HOLD, concrete progress, action,
and any one necessary user action.

## Choose a recovery action

For a routine local-only closeout, the Worker provides a concise inline report
with the order ID, base/candidate/actual remote SHAs, changed behavior and
limits, plus exact test commands and results. Include the bounded per-order
patch and test output inline when practical, or attach them through the same
Courier request. This is reported local evidence; Chat can assess whether it
supports the next bounded order without claiming remote verification of the
unpublished commit. Do not turn missing remote visibility alone into a
Supervisor review requirement. Published state and promotion still require
exact remote verification.

When the matching local-only closeout reply contains a proposed order that the
Supervisor explicitly declines on project scope, the Worker may send one
`followup --scope-reply-local-only --message-file <path>` with that decision and
a request for a bounded replacement. This path also accepts a fully captured
reply imported by `recover`: its `RECOVERED` label alone is not an unresolved
request. The command requires the matching completed Courier receipt and prior
local-only request, and retains unpublished ancestry. It is for a scope reply,
not for repeated requests when Chat has already answered the same question.

If a local-only closeout reply marks `GENERICCHESS_STATUS=COMPLETE` but says
only the current diagnostic/order is complete, the Worker continues the
project loop with one `followup --phase-complete-local-only --message-file
<path>` through the same Courier session. The note must identify the closed
phase and request the next bounded mainline order. This path checks the
matching completed receipt and retains unpublished lineage. Do not use it
when Chat explicitly states that no further GenericChess work is needed.

If a reconciled local-only closeout reply says `CONTINUE` but contains no
executable work order because it requests a Supervisor research-direction
decision, use one `followup --decision-reply-local-only --message-file <path>`
to relay that decision through the same Courier session. It checks the matching
completed receipt, absent work-order ID, and prior response hash, and retains
the unpublished candidate. Do not use this path to revisit an existing order.

An explicitly local-only closeout may receive `LOCAL_SUPERVISOR_REQUIRED`
because the Chat cannot independently inspect the unpublished commit. The
Supervisor reviews the local SHA, tests, original request, and matching reply.
If that reply contains no new work order, use `followup --reviewed-local-only`
at most once for that reply; the command verifies ancestry and records request
lineage. If the Chat again returns only the same remote-evidence notice, do not
repeat the request. Continue only the latest user-approved bounded work with
the registered Worker, retaining the Courier evidence for later closeout.
The Supervisor must repair or reconcile the missing-order path rather than
repeatedly expanding that work into a substitute Chat/Worker research loop.
This notice alone is neither a blocked Goal nor a HOLD.

If a work order forbids publication while Chat requires remote Git visibility
of that same local-only candidate before issuing another order, record the
conflicting evidence requirements as a shared order-path fault. Recheck the
matching request, reply, local/remote SHAs, and the one reviewed followup.
Do not resend equivalent requests, publish the prohibited candidate, or
rebind Chat merely to repeat the same remote-only gate. Check whether the
Courier prompt that wrapped the immutable request imposed a stale remote-only
condition; updating Courier affects future requests and never rewrites a
submitted request. Do not silently treat a patch or test log as remote
verification. Give the Worker a single bounded, independent
mainline bridge with a stop condition while the Supervisor seeks a concrete
compatible order path or a new authorized publication boundary. Record the
decision in local runtime state so the next patrol does not reopen the same
review loop.

Use the smallest action supported by fresh evidence; escalate the remedy if
the same fault persists. Fix a broken selector, launcher, status read, or
registration at its actual source. Resume the same Worker with gpt-6-luna /
high when it stops without a legal condition. Count only distinct work turns
after a clear continuation instruction; replace on the third consecutive
refusal, or immediately when its Goal is actually marked blocked. Retire the
old task before registering one successor with an active persistent Goal;
delete only if the app supports deletion, otherwise archive and report that
fact. Preserve the existing Courier session, request, worktree, and evidence.
If the Worker should have an active Goal but its Goal is inactive and cannot
be resumed in that task, replace the Worker immediately by the same procedure
and establish a fresh active Goal in the successor. Do not wait through hourly
patrols or count this as three refusals. First verify the actual Goal status
and the failed resume path; idle task status or unavailable Goal data alone
does not prove that restoration failed.

For Courier, first search for the exact submitted request and matching reply,
including durable receipts and the live target. A submitted or uncertain
request must never be silently resent or superseded. If matching output
exists, consume it. If proven unsubmitted, retry or supersede while preserving
the old request. If the old request is irrecoverable after bounded same-ID
reconciliation, the Supervisor may retire it and prepare one successor only
after recording why the old request cannot produce an unconsumed order,
linking both IDs, and retaining its evidence. If that cannot be established,
pause only that irreversible Courier operation and continue independent work.
When the target Chat itself is proven unusable, rebind within the same ChatGPT
project/profile and retain the old target for deduplication. Remove the old
Chat only if removal is supported without losing required evidence.

Do not ask the user to resolve a routine local error. When all available
repairs would have an uncertain irreversible effect, state the exact blocked
operation, evidence, independent work performed, and the single decision
needed. A Supervisor patrol remains responsible for revisiting the blocker.
