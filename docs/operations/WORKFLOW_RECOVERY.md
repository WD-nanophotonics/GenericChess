# GenericChess workflow recovery manual

This is an operational runbook under `AGENTS.md`, not a second policy source.
Use the current project policy and the latest user instruction if they differ
from a procedure here. `WORKFLOW.md` lists ordinary commands. Keep one Worker,
Courier session, worktree, and Heavy job. Do not turn an ordinary error into a
Supervisor HOLD or a blocked Goal.

## Supervisor attention budget

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
When Chat has no usable next order, the Worker sends the Supervisor the current
request evidence, one proposed bounded action, and its stop condition. The
Supervisor decides allow, deny, or replace with a narrower action and sends
that decision back to the Worker. Do not forward a routine scope choice to the
user or keep requesting new tests while no project question has been settled.

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

An explicitly local-only closeout may receive `LOCAL_SUPERVISOR_REQUIRED`
because the Chat cannot independently inspect the unpublished commit. The
Supervisor reviews the local SHA, tests, original request, and matching reply.
If that reply contains no new work order, use `followup --reviewed-local-only`
at most once for that reply; the command verifies ancestry and records request
lineage. If the Chat again returns only the same remote-evidence notice, do not
repeat the request. Continue the latest user-approved bounded work directly
with the registered Worker, retaining the Courier evidence for later closeout.
This notice alone is neither a blocked Goal nor a HOLD.

Use the smallest action supported by fresh evidence; escalate the remedy if
the same fault persists. Fix a broken selector, launcher, status read, or
registration at its actual source. Resume the same Worker with gpt-6-luna /
high when it stops without a legal condition. Count only distinct work turns
after a clear continuation instruction; replace on the third consecutive
refusal, or immediately when its Goal is actually marked blocked. Retire the
old task before registering one successor with an active persistent Goal;
delete only if the app supports deletion, otherwise archive and report that
fact. Preserve the existing Courier session, request, worktree, and evidence.

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
