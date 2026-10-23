# Local Agent operations

AGENTS.md owns current user authority, PUBLIC/reasons, safety/Agent boundaries,
stops, research integrity and duration rules. This file owns operating methods;
LOCAL_MAINLINE.md owns revisable research choices. Do not reconstruct current
policy from dated consultation history. Full pre-cleanup manuals remain at
Git4f6858b128e38c3b93360d78b7f5de6ad61af695; they are evidence, not active tasks.

## PRIMARY patrol, roles and communication —2026-10-23

PRIMARY_SANDBOX owns the mainline checkout, research clock, sandbox branch and
publication. DEV_AUX owns its existing sidemission checkout and outputs; do not
write its files, state, session, memo or unpublished work. This patrol covers
only PRIMARY mainline research and the existing project Chat.

The existing `genericchess` heartbeat recurs every60minutes by the explicit
latest2026-10-23 user direction, superseding its120minute cadence while preserving
its identity. Both existing roles are hourly; only PRIMARY files are updated here.
A one-time pause applies only to that inspection and never edits the
recurrence. Keep all user stop flags intact; a scoped stop is not cleared by a
heartbeat or role resume.

At each 60-minute PRIMARY patrol, read incoming messages/comments in the existing
GenericChess Chat and the relevant complete threads once. At every explicit
manual work start/resume, check for new incoming messages/comments before Main
unless this 60-minute patrol has already completed that read; never reread more than
once in the same 60-minute patrol. Preserve the exact project-related read in
ignored `.local_agent` before evaluating it. Treat Chat comments as suggestions
unless the user directly confirms a decision. Do not @Dot,
contact Dot in real time, wait/poll for Dot, or use a Dot-specific control path.
The2026-10-23 user direction restores asynchronous two-way Slack, superseding
read-only coordination. At substantive segment end/critical milestone prepare at
most one merged progress and genuine-question message per existing probe. Include
new evidence/negative results/UNKNOWN/cost, judgment, next action and fixed source
links plus FULL verified remote PRIMARY SHA. Evaluate whether an independent
Chat/Claude answer can change methods, interpretation, budget, boundaries or next
steps; state evidence, own view, options and exact decision. Do not fabricate a
question. Next original probe follows up unanswered questions and new replies,
recording adoption/defer/rejection and actual effects separately. Publish first.
Use the existing mailbox; reconcile old uncertain sends without automatic retry,
preserve original receipts and restore new legitimate exchanges rather than
silently abandoning communication. No Dot, real-time waiting, chasing, self-reply,
extra probe/worker or AUX reporting. >=120minute execution still waits for user
necessity assessment/confirmation; continue independent short work otherwise.

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
exactly two hours) requires the user's necessity assessment before starting. A real necessity question may accompany the single authorized asynchronous
report, but execute only after the user assessment/direct confirmation; continue
shorter independent work meanwhile. Do not split a run to evade this rule or confuse it
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
handling. Raw capture paths use the active session UUID plus a fresh read UUID;
final opaque bytes MUST use slack_transport.save_plugin_original, which refuses
a different existing original. Time-only names and direct replacing writes are
not safe across days/resumes. Read new project Chat messages/comments and relevant complete threads
once per 60-minute patrol; preserve the exact project-only output privately before
reconcile or adoption. A suggestion does not override current user policy or
become user authorization by itself. No @Dot, live exchange, response polling or
routine acknowledgment. For a >=120-minute run, include a real necessity question
only in the authorized single asynchronous progress message; execution still
requires the user's incoming assessment/direct confirmation. Do not wait/poll or
start before that confirmation; continue shorter independent work.

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
A matching RuleSet fingerprint does not make legacy and semantic action records
interchangeable. Replay with the recorded compilation route; explicit semantic
records use compile_legacy_ruleset_for_semantic_execution, not the default legacy
selector. Diagnose a route mismatch before changing actions or expectations.

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
fails, do not send. Sending is separately authorized by the2026-10-23 asynchronous two-way rule;
this publication sequencing remains mandatory.
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

## Observed2026-10-22 preparation and forecast corrections

A RuleSet boundary uses ruleset_to_dict/serialize_ruleset, not a generic dataclass
projection. Round-trip the exact saved canonical input before marking it ready;
null optional dimensions in a generic dump caused a zero-query setup failure.
For substantially larger full-node search panels, forecast from real full-node
calls on representative full histories, including reserves and recording cost;
cheap completed D1/D2 timings do not forecast a maxdepth64/node65536 call. A
cooperative whole cap preserves a bound, not planned coverage. Keep missing slots.

Use simple evidence file paths through generic-chess-local.cmd. Its IF block
forwards arguments to cmd; unquoted parentheses in no-space prose can be parsed
as batch syntax even after the Python CLI accepted a work interval. For such
prose use the existing .venv Python -m tools.local_agent.cli directly. After a
wrapper error inspect session status before retrying; do not double-credit an
already committed interval. No recorded times were rewritten for this incident.

An inactive feature does not require its default coefficient to be zero. Before
asserting that, inspect the actual consumer/profile constructor and distinguish
an explicit proved-zero override from the default complete table. The observed
capture-removal preflight kept finite default hand prices while stock stayed
unreachable; the source contract resolved the assertion before any Player call.
Never rewrite a product expectation solely to match a returned table.


## Pure-Leaper forward probe and actual interval ends —2026-10-22

Use scripts.leaper_design prepare/preflight/run on NEW ignored outputs. Existing
results/source hashes are frozen; do not refill completed/censored games. Material
mode requires complete frozen preflight-inputs.json histories and measures both
same-interface policies; defaultAB cost alone is not that gate. Current Main,
forecasts, actual source/data and further scope live in LOCAL_MAINLINE/report.
Use scripts.leaper_portrait --packet for exported action/PV/RNG/FLOOR replay;
shared Core validation is not an independent WDL engine. Do not rerun unchanged
fitness to repair recording or publication qualification.

For session work end timestamps use an observed actual UTC or generate
`datetime.now(timezone.utc).isoformat()` immediately before invoking the CLI.
Never guess a later minute from perceived elapsed time. A future-time refusal
adds no work; inspect status before correcting it, never assume it was credited.
Pure administration remains excluded. Scientific computation must have actual
bounded producer/output evidence, not just an ACTIVE flag or open UTC clock.
Inspect a producer poll before flushing its interval. If it reports CLOSED, cap
the compute interval at its saved actual execution end, not the later tool or
ledger call time. Do not chain that poll with an unconditional flush-to-now.
Start subsequent real analysis at its observed start and exclude the gap. Any
necessary ledger correction preserves the original bytes and a dated, explicit
old/new interval audit, uses the atomic helper and rechecks session status.

## Registered code counts and forecast arithmetic —2026-10-22

A batch's planned count is actual frozen input worlds times controller pairs,
roles and repetitions. Run uses that input count, never the fresh process's
fixed default PAIRS list; verify the plan before first execution. The observed
two-code counterexample reproduced60/40miscounts and IndexError at zeroqueries.
Do not change expectations to match those outputs. Preserve actual old producer
bytes. A necessary before-fitness caller repair must retain original registration/
cost provenance and demonstrate unchanged scientific inputs/slot sequence; old
cost returns are old returns, never extra calls or silently current-source ones.

Write exact forecast arithmetic before queries. If a frozen prose target is
ambiguous, preserve it and report plausible versions without selecting the best
posthoc result. Missing planned roles have intervals/undefined means, not0.
Separate an empirical whole-game cost estimate from a worst-call coverage bound;
retain both methods/results and the already frozen hard cap, never widen a cap
or use a renamed run to hide failures. Current route/evidence stays in Mainline.

For the actual resource-response probe, registration.search_variants explicitly
maps a controller label to its base evaluator and counted-node budget. The
preflight_policies list must cover those actual search variants on complete
histories; returns record base_policy and node_budget. Do not infer both actors'
budgets from the registration.nodes fallback or equate nodes with wall cost.
The sampled-call forecast must count both search actors for AB/AB, not apply the
old half-game search count from AB/Random. Even the corrected sampled maximum is
not a future per-call bound or total recording/controller-cost guarantee. Keep
the original forecast and actual returns when correcting a diagnosed calculation;
do not silently rewrite an executing registration or extend its cap.
Node-only deterministic AB/AB games do not consume the actor RNG streams.
Changing seeds therefore supplies no designed independent replication. Count
physical executions and unique complete records separately. Do not silently
reset/refill an executing plan. An observed-redundancy early stop must retain
every unexecuted planned slot as UNKNOWN and record its actual cause; never
clone an outcome into a paid execution. Remove redundant repeats from a future
zero-fitness plan with its original registration and reason retained. A reflected rule has a
new identity fingerprint; compare actual profile coefficients separately from
that identity, and verify the explicit physical mapping before claiming symmetry.

For representation cohorts, an explicit input seed_world retains the original
code index when worlds are flattened. Omitting it preserves the existing formula.
Do not accidentally change actor streams by renumbering representations, or
claim identical paths after legal-order/history divergence. Geometric D4 averaging
does not also average type-label encodings. Profile coefficient equality and
reached canonical-Evaluator covariance are separate from full Native leaf or
bounded-policy equivalence; keep the actual scope of each check.

## Observed opening-history and registration contracts —2026-10-23

Forward run inputs can carry a nonempty initial_record. Replay it with the strict
GameRecord boundary; never construct a fresh empty GameSession for that input.
Keep the full prefix, history/repetition and absolute rule clock. Qualification
checks its preserved prefix and only pairs new suffix queries/actions; portraits
start from the retained record. Absolute plies and suffix queries/captures differ.
A real red regression observed [] replacing two actual legal opening actions;
fix the caller contract, not that expectation. Empty-record behavior is retained.

When changing an experiment arm, construct coherent question/hypothesis/selection/
pairs/cost prose BEFORE queries. Do not wholesale-inherit a different arm's
baseline claim. If stale prose is discovered after launch, preserve the original
registration, annotate the exact conflict, and do not claim that old comparison
as preregistered or alter actual slots/results/caps. seed_world may deliberately
share actor streams: audit the ACTUAL seed formula for opening as well as geometry
cohorts, disclose correlations/duplicate weights, and never call physical repeats
iid. Old cost references are not new calls; a sampled maximum is not a later-call
bound. Export review checks actual copied files, full inputs and literal policies;
source capsules remain data and must not be executed or unpacked by the reader.


## Explicit forward-control protocols —2026-10-23

The probe-only `floor_coupling=physical_type_xy_v1` requires a complete frozen
`world.floor_type_map`, full plain-Leap/remove rule validation and unique actual
Core actions. Omission preserves old literal FLOOR behavior. Physical rank
sorting preserves the uniform no-win law; sorting multiple immediate winners
preserves their payoff, not the old deterministic winning action. Keep all rule
and history identities; this is not a generic canonicalization or product API.
Published games retain the explicit protocol/map, and the packet reader binds
these to registration/inputs while independently replaying the chosen ranks.

`search_variants[label].depth` explicitly requests a positive depth up to64;
omission keeps64 and the old counted-node route. Record `requested_depth` beside
actual `completed_depth`, termination reason and nodes. Root-immediate-win depth0
is an early terminal witness, not an achieved fixed-depth search or missing game.
A finite adjacent-depth mean is not automatically a transitive strength chain.

UNIT/MOBILITY controls use the same leaf/order adapter as Static, keep Static
ordering and other leaf terms, and freeze complete candidate profiles before
queries. State the admitted no-promotion/drop/remove domain. Independent finite
board destination counts and exact leaf material differences qualify inputs;
no-op prices must preserve actual deterministic trajectories. Do not turn a
zero-containing interval, root invariance or these utility panels into a learner
gate. Keep OLD references distinct from NEW cost/fitness executions.

A registered empirical whole-game cost screen is distinct from the caller's
maximum-sampled-call forecast. Freeze the decision method before queries,
preserve both original forecasts/results, and retain the cooperative cap and
UNKNOWN. A pre-fitness full-history cost supplement preserves its own registration,
root draws and original returns; charge its new costs against the same experiment
budget. It never permits extending a cap, replacing fitness roots or filling slots.


## Total work and data-only replication —2026-10-23

PlayerDecision.nodes and qnodes are separate fields; SearchLimits.max_nodes
counts their SUM. Preserve reported search, outer query and complete recording
clocks separately. A smaller budget may require more turns. Requested/completed
iteration depth, forced-check extensions and selectiveTT reuse do not establish
uniform leaf depth or WDL. A derived mixture/role reference is not a new execution.

Use scripts.leaper_calibration_run --materialize-from-packet --group --output
for explicit zero-query data preparation into a NEW directory. It never executes
source capsules. Keep the original registration; record new serialization SHA,
actual preparation time and provenance, not an old hash for different bytes.
The execute stage still requires recorded library source and frozen cost/cap
checks. Current scientific selections remain in LOCAL_MAINLINE.md.

## Empirical cost override qualification — E0 observation2026-10-23

The stopped1920slot small-rule E0 panel accepted an unsupported1600second
aggregate over a38995second sampled-maximum forecast. Neither a frozen guessed
number nor a generic entry accepting it makes that empirical gate scientifically
valid. Preserve that cost-feasibility failure, all partial/missing slots and the
original cap; never resume/refill it. For any NEW empirical override bind actual
comparable full-game records, executed source, controller/history/clock conditions,
scaling/reserve and total preparation/preflight/validation/analysis cost. If that
basis is absent, stop at cost feasibility or redesign a smaller genuinely new
question before fitness. Do not split the old scope or bypass the120minute rule.


## Observed Q0 and counter contracts —2026-10-24

A configured quiescence hard-depth of8 does not enable check extensions. In
SearchTuning, use_check_only_qsearch defaults FALSE. At ordinary qdepth0 this is
static leaf evaluation; checked leaves extend only with that explicit switch.
The maintained semantic_probe_cost caller now exposes --check-only-qsearch;
omission preserves its old behavior. Ordinary Q4 is another leaf policy, not
an equivalent main depth. Preserve the original source/returns when correcting
an inaccurate forced-check description; do not rerun a closed experiment to
repair its wording.

The current leaper_design forward caller supports static Q0 only. Its future
registrations explicitly state check_only_qsearch=False; legacy
forced_check_depth=8 means a configured hard limit. It now rejects a registration
requesting another q policy/hard limit instead of silently running Q0. This does
not change old actual policies or activate extensions in any existing game.
Other historical callers require their own executed-source review.

nodes+qnodes is the implemented budget-event sum. A main leaf entering qsearch
can count the same physical position in both fields; these are not distinct
states or equal-cost operations. The runtime's compatibility field
position_keys_computed mixes searched-successor bookkeeping with TT key requests;
it is not a count of SHA calculations. Explicit legal requests include cached
lists and aborted attempts; action-output counts can repeat a cached frontier.
Native success counts are not all attempts, so their difference is not an exact
cache-hit count. Keep nested/root/profiler cumulative times separate, and call
unassigned outer time a residual until measured. Current evidence and scoped
source interpretation live in LEAPER_POLICY_COST_AND_QUANTITY_20261024.md.
