# Local Agent operations

AGENTS.md owns current user authority, PUBLIC/reasons, safety/Agent boundaries,
stops, research integrity and duration rules. This file owns operating methods;
LOCAL_MAINLINE.md owns revisable research choices. Do not reconstruct current
policy from dated consultation history. Full pre-cleanup manuals remain at
Git4f6858b128e38c3b93360d78b7f5de6ad61af695; they are evidence, not active tasks.

## PRIMARY patrol, roles and communication —2026-10-20

PRIMARY_SANDBOX owns the mainline checkout, research clock, sandbox branch and
publication. DEV_AUX owns its existing sidemission checkout and outputs; do not
write its files, state, session, memo or unpublished work. This patrol covers
only PRIMARY mainline research and the existing project Chat.

The existing `genericchess` heartbeat recurs every90minutes by the explicit
2026-10-21 user direction, replacing hourly cadence and preserving its identity.
A one-time pause applies only to that inspection and never edits the
recurrence. Keep all user stop flags intact; a scoped stop is not cleared by a
heartbeat or role resume.

At each 90-minute PRIMARY patrol, read incoming messages/comments in the existing
GenericChess Chat and the relevant complete threads once. At every explicit
manual work start/resume, check for new incoming messages/comments before Main
unless this 90-minute patrol has already completed that read; never reread more than
once in the same 90-minute patrol. Preserve the exact project-related read in
ignored `.local_agent` before evaluating it. Treat Chat comments as suggestions
unless the user directly confirms a decision. Do not @Dot,
contact Dot in real time, wait/poll for Dot, or use a Dot-specific control path.
All coordination is read-only: do not send consultation messages, @mention anyone
or solicit a reply. A >=120-minute run still needs its necessity assessment; wait
for an incoming user Chat message or direct user confirmation before starting it,
and perform shorter independent work meanwhile. No new channel, sender, worker or
timer.

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
   A model switch uses the same session protocol. An active record left by a
   previous final reply is an incomplete handoff, not proof of continuous work.
   Never count its offline span. This user-requested workflow repair is bounded
   administrative work; it does not do or accrue the unfinished research.

NEXT_WORK.md <=20lines/2048 UTF-8 bytes, one each State/Segment/Main/Backup1/
Backup2/Evidence. Each task has four nonempty fields separated by |:
question | immediate action | expected evidence | done condition.
Keep distinct executable tasks and the critical current decision/reason
(PUBLIC for Chat access; PRIVATE abandoned). Other current decisions live in
AGENTS.md. Replace stale tasks/evidence; shorten detail rather than losing the
causal relationship. Missing memo is rebuilt from evidence before research.
Update the memo in place; do not delete it before creating its replacement.

## Shared configuration writes

Use the existing tools.local_agent.common.write_json for every mutable JSON
update, including ad-hoc rollout/session/handoff updates. Serialize to a sibling
temporary file and replace the target atomically; never truncate shared flags
with Path.write_text/write_bytes or json.dump to the live file. Read and preserve
current stop/ownership fields before updating owned segment metadata. A failed
replace leaves the previous target authoritative; report the error, not success.
This protects readers from a zero-byte/partial target, not multiple-writer races.
PRIMARY remains the sole writer here; never edit another checkout's flags.

On2026-10-16 at20:11UTC AUX observed a zero-byte PRIMARY rollout. PRIMARY's
ad-hoc non-atomic end-of-segment write occurred at the matching time; the tool
receipt does not prove every OS writer, but this identified unsafe own operation
is corrected. Existing CLI writes already used the atomic helper. Preserve the
failure evidence and current valid flags; a later valid read does not erase it.
Regression controls cover a concurrent pre-commit reader and failed replacement.

## Research checkpoints and cost

session checkpoint --question Q --observation NEW --evidence REF --next-action ACTION
Use --kind research|documentation|transport honestly. Only actual research is a
research stage; old conclusions, Slack receipts and document saves are not new
science. The current segment retains all checkpoints; purpose reports retain
full evidence. Do not print its full history
or a broad tool catalog into context when a small relevant selection suffices.
Do not reset active clocks, fabricate stages or reinterpret elapsed App time as
effective work. A soft block triggers a useful backup, new source or bounded
hypothesis check, not an unchanged rerun or early exit.

Record actual intervals promptly (before a checkpoint, compaction or handoff):
`session work --started-at <UTC ISO> --ended-at <UTC ISO>
--activity research|analysis|validation|documentation|transport|administration
--evidence <concrete command/result/artifact reference>`.
Only the first three categories accrue effective research time. Validation must
serve substantive research, not repeatedly rerun an unchanged passing test.
Record only observed active work; split around idle/waiting/admin periods. An
evidence string is not permission to label an entire open clock as work.
Overlaps, future timestamps, naive timestamps and intervals before this resume
window are rejected. `session start` preserves UUID/start and prior intervals,
opens a new recording window, and credits no time automatically. Flush known
work before an intentional recovery boundary. Unrecorded legacy work stays
unverified; do not retrospectively assume 28 minutes of UI uptime was all research.
`session status` reports `wall_minutes` separately from `effective_minutes`.
The 60-minute gate uses exact recorded seconds, not rounded display minutes.
CLI start/status/interrupt/finish outputs omit full checkpoint/work histories by
default; `session status --full` is available for a deliberate bounded audit.

Before a bounded batch record the unknown, decision-changing possible outcomes,
resource estimate and cheaper alternatives. Include preparation, recording and
engineering overhead. Development limits are cost checkpoints, while permissions,
machine safety and frozen fair-comparison caps remain hard boundaries. Do not
extend a frozen experiment or erase its failure by renaming seeds/phases.
Use existing recorders/atomic writes; no new framework merely for receipts.
Small training is authorized. Estimate the single experiment/run BEFORE starting:
expected duration <120 minutes needs no prior assessment; >=120 minutes (including
exactly two hours) requires the user's necessity assessment before starting. Do not
send a request or follow-up; read only an incoming user Chat message or direct
confirmation, and continue shorter independent work meanwhile. Do not split a run to evade this rule or confuse it
with segment duration. The user's 2026-10-20 direction replaces the former live-review route; the older >1hour threshold is superseded.

Persist each newly returned decision or timing batch atomically BEFORE downstream
validation/assertions; preserve the return even when its interpretation fails.
Finish and save each immutable scientific input before marking its execution
context ready. Distinguish generation failure from profile/metadata/capture
failure; a successful in-memory context is not proof that its input was saved.
On harness repair reuse preserved completed records, leave irretrievably missing
returns explicit, and do not replay frozen fitness or timing merely to refill.

Inspect completed result files, not a large report being atomically replaced by
its producer. A Windows read can block replacement. Monitor producer stdout or
use a reader sharing delete access; preserve interrupted cases separately from
budget-censored ones. Measure actual disk use before removing only redundant
owned output; never delete unique evidence or user files blindly.

For cold q0 node forecasts, include paid root scanning and the inclusive abort
boundary: absent early wins/root declarations/warm TT, observed completedD1
needs2N+2 nodes with scanON orN+2 OFF. This does not forecast wall completion
or qsearch. Charge full import/generation time and preserve existing frozen caps.
When OS pytest temp/cache access is refused, retain the actual setup errors and
use supported cache_dir/--basetemp options in a fresh ignored project directory;
verify the target before reuse, never alter machine security/ACLs or live flags.
Keep units explicit:120seconds is2minutes; the single-run consultation threshold
is7200seconds. This does not change the60–90minute Agent work-segment rule.

For sub-millisecond caller measurements use perf_counter; a sub-resolution zero
is not zero cost. Restored Python-S drivers need their declared external vendor
dependencies and explicit source origins, with no editable-project fallthrough
or fake stop trees. Preserve setup failures before repairing the disposable
runtime layout; resume only affected stages when source/data hashes remain
unchanged. Do not extend experimental caps or rerun frozen fitness to fix a
qualification harness. Record multi-phase qualification and actual costs honestly.

## Chat messages and collaboration

For tool discovery, list matching tool NAMES first, then inspect only the chosen
tool's schema. Do not dump broad matching descriptions/embedded full logs into
context. Follow SLACK_WORKFLOW's raw-response preservation before processing.

Use `docs/operations/SLACK_WORKFLOW.md` for the active read path and raw-read
handling. Read new project Chat messages/comments and relevant complete threads
once per 90-minute patrol; preserve the exact project-only output privately before
reconcile or adoption. A suggestion does not override current user policy or
become user authorization by itself. No @Dot, live exchange, response polling or
routine acknowledgment. For a >=120-minute run, do not send a question. Wait for an incoming user Chat
message or direct confirmation before starting; continue shorter independent work.

Coordinate with the existing DEV_AUX only for concrete dependencies, blockers or
useful findings. Do not edit its checkout/state or duplicate its solver/learning
lane. At completed segments update `COLLABORATION_LOG.md` with observed
contributions, actual coordination, corrections, adoption and limits. Read source
and results at a fixed revision; distinguish publication from someone reading or
independently executing the work. Keep the repository PUBLIC for Chat readers.

## Existing complete-state cost caller

Use scripts/semantic_probe_cost.py with full canonical --input records and a NEW
output path. Existing optional --pvs, --countermove, --aspiration-delta <positive N> and
--staged-move-picker expose current switches; omission preserves defaults.
--evaluation-backend unit explicitly supplies1000CURRENT-board/900BASE-hand,
metadata-anchor0 prices for ALL declared/future types with bonuses OFF. It does
not silently change default profile admission or establish price quality.
The caller saves immutable inputs before setup/query, preserves error/traceback
and missing slots before rethrowing, and retains actual returns before validation.
For service costs separate actual source/q policy, cold process/player/warmTT
state and first-call order. Whole runner elapsed time may include recording
cost absent from inner search time; use the declared qualification clock, retain
both originals, never relax its threshold or rerun a frozen panel to hide failure.
Repository text is UTF-8; specify encoding explicitly when reading/editing it
on Windows rather than using the platform Python default.

## Publication

Do not change a test's expected number to the observed number without locating
the intended contract and causal implementation/history change. A file being
outside the current diff, or an old git-blame date, proves neither that the
assertion is stale nor that the new output is correct. Preserve the original
failure and give the next worker an executable diagnosis task; do not silently
weaken tests or ask the user to reauthorize ordinary diagnosis. Respect a real
tool rejection, describe its precise scope, and continue permitted investigation.
Repeat passing tests only after meaningful changes, a new unresolved concern,
or the required publication gate; documentation formatting is not a reason to
repeat the same large suite.

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
Before any separately authorized outbound project Chat message/comment, publish
the referenced project changes first and verify the full remote SHA; if publish
fails, do not send. This is sequencing only and does not override the current
read-only communication rule or create send authorization.
The tested entry fetches, checks ancestry, tests, pushes and verifies the full
origin/sandbox SHA. Direct pushes are rejected by the existing hook; do not
bypass it. Verify independently with git ls-remote origin refs/heads/sandbox.
No force-push or automatic untested master promotion. Report actual failures.
Keep unrelated unfinished changes out of a bounded document delivery; if owned
changes are temporarily stashed, restore them and verify exact file hashes.

## Stop on failed native commands before publication

A native Python error does not stop default PowerShell execution. Run content
review, inspect its successful result, commit, and publish as SEPARATE sequential
checked operations. If commands must share a script, test $LASTEXITCODE after
EVERY native command and throw on nonzero; ErrorActionPreference alone is not
a sufficient native-exit guard. A failed review must never be followed by commit
or publish. This is operating correctness, not a new approval/consent queue.
For publication copies use an exact technical-member allowlist, not all-JSON
globs over private diagnostic directories; inspect actual contents as AGENTS
requires. Source origin by itself does not revoke the user's project-data grant.
The2026-10-17 first Native TDpacket violated this through two incidental local-path
JSONs. CurrentV2 excludes them; the bad commit remains historical evidence and
must not be restored/retried. No force/history rewrite without NEWuser authority.

## Finish, real limits and failure reporting

Before final RESEARCH reply:
session finish --reason REASON --evidence REF
session final-check
Inspect both exit codes/results. An active session always fails final-check;
leaving it active and promising the next heartbeat is not a valid final reply.
Normal safe_checkpoint/no_viable_action requires>=60 recorded effective minutes,
fresh research, a valid memo reserve and a matching quality review JSON. Continue
useful work toward90 then stop safely, no idle
padding. no_viable_action requires two fresh substantive alternatives, supplied
with --alternative Q twice and matching recent checkpoint questions.
Refusal means continue, not bypass. Tests/docs/publish alone are not ending reasons.
Explicit bounded user repair/configuration requests retain their bounded scope.

For normal finish REF is a JSON file with `session_id`, `ending_reason`,
`reviewed_at` (timezone-aware ISO after the latest work/finding),
`reviewed_work_intervals` (all recorded intervals including non-counting ones),
`effective_seconds` (exact ledger total), `old_conclusions_excluded: true`,
`research_questions` (nonempty list matching current fresh research checkpoints),
`limitations` (nonempty text) and `unresolved_issues` (list). Review the substance,
not just the fields. A stale/mismatched review or a bare 'tests passed/published'
cannot pass. Do not label old findings as research to satisfy this structure.

Only when a direct user message redirects to bounded repair/review/configuration:
save a JSON with `session_id`, `reason: user_redirect`, `requested_task`
(`repair`, `review` or `configuration`), `user_instruction`,
`instruction_reference`, and `observed_at`; invoke `session interrupt --evidence
<file>`. It records an INCOMPLETE interruption, not a normal finish or a new
60-minute research segment. Complete the bounded request, then run
`session final-check --mode bounded`. Next research `session start` resumes the
same UUID/start and recorded effective work, excluding the interruption gap.
Immediately after every state transition, run `session status` and reconcile
NEXT_WORK.md: copy the actual state, same UUID and UTC start/resume, exact
effective seconds/minutes, interval count, and legacy-unverified status. The JSON
ledger is authoritative; the memo is a handoff and must never contradict it. An
interruption preserves earlier verified intervals but adds no repair time. Before
final reply/handoff, verify the memo and final-check refer to that same state.
Do not invoke interrupt merely because an ordinary patrol reached a milestone,
had no Chat comment or ran out of ideas. Actual runtime interruption must be
reported honestly; no helper can force a model/tool to remain available.

Early reasons: user_stop, user_decision, tool_limit, quota_limit, runtime_limit,
scientific_complete. Stop wins immediately. A missing idea/formula or old launch
failure is not a necessary user decision or runtime exhaustion. A sudden platform
interruption may leave an incomplete active record; recovery must exclude the
unobserved gap. It is not an authorized early final. After an accepted finish
update memo status/start/reason; explicit bounded redirects use interrupt above.

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

For archived source inspect hard-coded personal directory literals as well as generated JSON/logs, including doubled Windows backslashes. A passed narrow filename exclusion does not establish all-member privacy. Preserve originals privately and qualify sanitized source copies separately; never claim old Git history was purged by a normal deletion commit.
