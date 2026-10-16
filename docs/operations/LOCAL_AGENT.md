# Local Agent operations

AGENTS.md owns current user authority, PUBLIC/reasons, safety/Agent boundaries,
stops, research integrity and duration rules. This file owns operating methods;
LOCAL_MAINLINE.md owns revisable research choices. Do not reconstruct current
policy from dated consultation history. Full pre-cleanup manuals remain at
Git4f6858b128e38c3b93360d78b7f5de6ad61af695; they are evidence, not active tasks.

## Start, recovery and memo

1. Read .local_agent/NEXT_WORK.md in full, AGENTS.md, LOCAL_MAINLINE.md and
   rollout/advisor/slack stop flags. Latest user direction wins. Reconcile
   decision + reason + superseded alternative + execution consequence before
   acting. Never clear a stop merely to resume.
2. For RESEARCH use generic-chess-local.cmd session start. session.json owns
   UUID/UTC start; active same-chat segments retain both after compaction.
   Another chat cannot take over. Explicit bounded configuration/review/repair
   is not a60–90minute duration sample and must not reset a research clock.
3. Execute Main, validate and assess the result, checkpoint and begin the next
   decision-changing step. No extra writer, Goal, scheduler or restart loop.

NEXT_WORK.md <=20lines/2048 UTF-8 bytes, one each State/Segment/Main/Backup1/
Backup2/Evidence. Each task has four nonempty fields separated by |:
question | immediate action | expected evidence | done condition.
Keep distinct executable tasks and the critical current decision/reason
(PUBLIC for Dot/Chat access; PRIVATE abandoned). Other current decisions live in
AGENTS.md. Replace stale tasks/evidence; shorten detail rather than losing the
causal relationship. Missing memo is rebuilt from evidence before research.

## Research checkpoints and cost

session checkpoint --question Q --observation NEW --evidence REF --next-action ACTION
Use --kind research|documentation|transport honestly. Only actual research is a
research stage; old conclusions, Slack receipts and document saves are not new
science. The helper retains recent details; purpose reports retain full evidence.
Do not reset active clocks, fabricate stages or reinterpret elapsed App time as
effective work. A soft block triggers a useful backup, new source or bounded
hypothesis check, not an unchanged rerun or early exit.

Before a bounded batch record the unknown, decision-changing possible outcomes,
resource estimate and cheaper alternatives. Include preparation, recording and
engineering overhead. Development limits are cost checkpoints, while permissions,
machine safety and frozen fair-comparison caps remain hard boundaries. Do not
extend a frozen experiment or erase its failure by renaming seeds/phases.
Use existing recorders/atomic writes; no new framework merely for receipts.
Small training is authorized. A single project run expected>1hour first obtains
Dot's necessity assessment; continue shorter independent work while pending.
Do not split the run to evade this rule or confuse it with segment duration.

Inspect completed result files, not a large report being atomically replaced by
its producer. A Windows read can block replacement. Monitor producer stdout or
use a reader sharing delete access; preserve interrupted cases separately from
budget-censored ones. Measure actual disk use before removing only redundant
owned output; never delete unique evidence or user files blindly.

## Slack consultation and collaboration

Use docs/operations/SLACK_WORKFLOW.md for exact request/receipt/reconcile commands,
identity and pagination. Sole channel C0C6L21UU20; PRIMARY_SANDBOX and DEV_AUX
share the verified account. Labels route messages, not process authentication.
No per-message challenges. Read new roots plus full relevant/completed threads,
with pagination coverage. Save exact originals in Git-ignored .local_agent BEFORE
parsing/reconcile; local raw storage is expressly authorized. Long threads use limit20
with server cursors: a large response falsely claimed complete while omitting
replies. Validate actual counts with the existing strict parser before coverage
claims; preserve refused output and reread exact small pages, never reset/rebind.

User-directed inquiries use NEW AGENT_REQUEST/new REQUEST_ID/new thread.
Evidence-based Agent followups may retain the root with a unique FOLLOWUP_ID.
Information-only EVIDENCE/RESULT are not new consultation requests. No routine
acknowledgements or automatic retry/self-reply loops. Reconcile uncertain sends;
record actual receipt, purpose and duplicate risk before a reasoned recontact.
Dot silence is not a stop/publication gate. Daily10:00 Tokyo is the main window;
if no turn is active use its first later continuation, no missed-day catchup.
One native90-minute same-chat heartbeat resumes without a second writer.

Communicate with existing DEV_AUX only for dependencies, blockers or useful
results. Do not edit its checkout/state or reproduce its solver/learning lane.
At completed segments update COLLABORATION_LOG.md with contributions, actual
coordination, corrections, adoption and limits. Read source/results at a fixed
revision. Do not call delivery, source review or another Agent's tests independent
execution. Public repository access enables review; Slack attachments alone do
not prove whole-repository access. Keep PUBLIC unless a NEW user direction says
otherwise; PRIVATE rollback history is not a retry procedure.

## Publication

Continuing authority covers ANY project content without personal information,
passwords or credentials. Record origin is not a prohibition. Preserve exact
private originals and check/sanitize outgoing copies, including archives/history.
No per-file/message/push consent, even after compaction. AGENTS.md does not disable
platform enforcement; state the actual grant when requesting supported escalation.

Inspect the NEW commit's author AND committer metadata before publication as
part of the actual personal-information check. An observed inherited personal
Git email was caught before push. For Agent-generated commits use an explicit
nonpersonal Agent identity through command-local GIT_AUTHOR_NAME/EMAIL and
GIT_COMMITTER_NAME/EMAIL; do not change the user's global Git configuration.
If correcting metadata, amend only an owned, confirmed UNPUBLISHED commit.
Do not force-push or rewrite already published history. Preserve the original
local diagnostic privately and verify the new outgoing commit metadata.

Review diffs/history and relevant tests, commit only the intended delivery, then:
generic-chess-local.cmd publish --tests <relevant pytest targets>
The tested entry fetches, checks ancestry, tests, pushes and verifies the full
origin/sandbox SHA. Direct pushes are rejected by the existing hook; do not
bypass it. Verify independently with git ls-remote origin refs/heads/sandbox.
No force-push or automatic untested master promotion. Report actual failures.
Keep unrelated unfinished changes out of a bounded document delivery; if owned
changes are temporarily stashed, restore them and verify exact file hashes.

## Finish, real limits and failure reporting

Before final RESEARCH reply:
session finish --reason REASON --evidence REF
Normal safe_checkpoint/no_viable_action requires>=60minutes, actual research and
valid memo reserve. Continue useful work toward90 then stop safely, no idle
padding. no_viable_action requires two fresh substantive alternatives, supplied
with --alternative Q twice and matching recent checkpoint questions.
Refusal means continue, not bypass. Tests/docs/publish alone are not ending reasons.
Explicit bounded user repair/configuration requests retain their bounded scope.

Early reasons: user_stop, user_decision, tool_limit, quota_limit, runtime_limit,
scientific_complete. Stop wins immediately. A missing idea/formula or old launch
failure is not a necessary user decision or runtime exhaustion. Preserve active
session on interruption; after a normal finish update memo status/start/reason.

For user_decision/runtime_limit the helper requires a JSON evidence file bound
to active session_id and observed_at, containing failure, diagnosis, impact,
attempted_fixes, cannot_continue and evidence_reference. user_decision additionally
needs user_request.sent=true, action, reference and why_agent_cannot_do_it tied to
an actual delivered user-visible request. runtime_limit needs
actual_runtime_exhausted=true and limit_kind runtime_shutdown/runtime_expired/
resource_exhaustion backed by THIS run. Old evidence/resume settings do not prove
failure. Scientific completion requires actual research, whole_current_objective,
remaining_work=[], conclusion/evidence_reference, and mainline Science is COMPLETE
without Science is OPEN. A local milestone is not whole-objective completion.
Structural validation cannot authenticate truth or guarantee App uptime.

For serious failures report proactively: exact error/evidence, affected work,
checks/fixes and outcomes, confirmed cause versus uncertainty, specific user steps
needed and recovery verification. State when no user action is needed. Diagnose
what existing authority permits, keep independent work moving; no concealed block
or repeated unchanged launch. A Windows4551 symptom does not by itself identify
Smart App Control: inspect relevant CodeIntegrity evidence for THIS project's
path, distinguish policy/permissions/dependencies. Machine-wide security changes
remain the user's decision. Prior incidents/three segment-duration acceptance
samples and old cost thresholds are retained at the fixed historical Git above;
they are not new obstacles or scientific admission criteria.

## Repository and configuration

REPOSITORY_LAYOUT.md owns active/history layers; default pytest covers
product/development/workflow/specification. Old receipt tests are history.
Use existing project pyproject.toml/build script and normal supported dependencies.
Project permission text is not a global enforcement setting. No new TOML policy,
automation, external service, ownership framework or scheduler is needed here.
Recovery evidence remains REBUILD_20261003.md; do not import old App databases,
credentials, Goals or retired queues. Current hardware load is normal concurrency,
not permission to alter other projects or demand exclusive timing windows.
