# Local Agent operations

AGENTS.md is the sole active policy. The user approved broader exploration,
time plus executable work reserves, and a small local work-segment validator.

## Start and resume

Read NEXT_WORK.md first, policy, current mainline and persisted stop flags.
Normal manual starts and heartbeat wakes start/resume RESEARCH, not just patrol.
Use `.venv\Scripts\python.exe -m tools.local_agent.cli session start`.
It checks stop flags and compact memo structure. An active same-chat segment
retains its UUID/start; a different chat cannot take it over. An ended segment
gets a new start. Never use configuration work as a duration sample.
Inspect session status after compact; session.json is authoritative for time,
not the memo's copy. Do not start a second writer when a turn is already active.

## Compact memo and task reserve

NEXT_WORK.md is <=20 lines/2048 UTF-8 bytes with exactly one each:
State, Segment, Main, Backup1, Backup2, Evidence. Each task has four nonempty
parts separated by `|`: question, immediate first action, expected evidence,
done condition. Three tasks must be distinct and genuinely executable; the
validator checks structure, the Agent checks scientific usefulness. Overwrite
completed/superseded entries; no memo history, rule repetition or per-version
archives. Detailed evidence belongs in research documents/Git. Tasks are
revisable reserves, not work quotas or an approval queue.

## Research loop

Execute Main immediately. Validate each milestone, assess mainline impact,
record checkpoint and actually begin the next task. CLI:
`session checkpoint --question Q --observation NEW --evidence REF --next-action ACTION`
Use `--kind research|documentation|transport`; only research counts as a
research stage. New primary-source analysis can be research; an old conclusion
re-read, Slack receipt or document save alone cannot. Duplicate observations
are rejected. Keep the last6 checkpoint details; full evidence lives elsewhere.

Soft blocks (missing formula, failed probe, old restriction, unanswered dot)
trigger backup work or active exploration. New explicit approximate hypotheses
are allowed without a complete WDL bridge or uniquely rule-given population.
Freeze a proposed empirical test before observing its validation evidence;
keep old failures and report assumption-dependent conclusions accurately.
Revisit old routes only with a changed premise and a decision-changing test.
Do not tune exposed/human labels, read the Xiangqi human holdout, rewrite frozen
experiment conditions, repeat unchanged failed batches or substitute framework
work for science. Development continuation follows the Budget section below.

## Budget

User2026-10-06 requests value per cost rather than universal time/count gates.
Dot's complete reply was read, reconciled and adopted in the same Slack thread:
https://nanomelon.slack.com/archives/C0C6L21UU20/p1791260944221889
Request GC-SLACK-20261006-132838-03368ffa; raw reply remains in the ignored
local Slack record. Dot reviewed the request/user preference and earlier public
cost records; it did not run today's69-edge tree or change machine permissions.

Use a short continuation record: what is unknown; which possible outcomes change
the next decision; expected incremental resources. Include implementation and
explanation/token costs. No numeric ROI fiction or new approval framework.
Within existing authorization, an interruptible small batch may continue past
a development cost checkpoint when it has concrete information value. Record
actual transitions, cache accesses, scoring, time and bytes separately:129 as
a conservative upper bound is not129 measured transitions.128/5000/15seconds
are not universal scientific thresholds;60-90minutes remains the user's active
research-continuation target, not an experiment-value or machine-safety metric.

Keep permission, stop flags, finite machine-safety protections and formally
declared comparison conditions. Discuss material new cost, long machine
occupation or uncontrolled growth before proceeding; no heavy jobs/extra worker
or access bypass. Preserve all old frozen trials and failures. Additional
development must explain changed premises and its adaptive/exposed status;
renaming phases/seeds cannot restore an independent holdout. Report favorable,
unfavorable and unchanged outcomes alike. Give candidate and baseline the same
resource condition or show resource/result curves. Pause a route whose possible
outcomes no longer change decisions; choose useful independent work instead.

Exploratory development measurements may be useful without exact WDL, complete
all-defense certificates or an unexposed holdout. Label their limitations and
reserve those stronger requirements for stronger claims. Prioritize a runnable
candidate with a fixed existing search configuration and common comparison
entry; reuse existing recording/state helpers. Broader proofs and new adapters
should address an observed failure or explicit use, not precede all useful tests.

User2026-10-06 explicitly requested review/discussion of dot's efficiency
diagnosis. Adopt its practical priority: one repeatable candidate/search comparison,
then failure-driven improvements. Start with a declared tactical development batch;
hold rules, horizon, ordering/TT and resource conditions equal across evaluators.
Record concrete tactical errors, selected moves, completeness and cost. Internal
score differences or no short mate alone do not measure playing improvement.
Short games/external references may follow through the same entry; depth2 smoke
tests do not establish amateur strength or generic-rule transfer. Keep exposed
data exposed and old proofs intact, without requiring new per-case admission
reports. Ask dot for a critical objection and one useful next action; do not
automatically turn its possible risks into tasks. Consultation is not approval.

Same-thread followup efficiency-20261006-01 received a complete dot reply at
14:04:28 JST (sent14:03:47;41seconds), read all6 posts and preserved raw output.
Adopt: use existing tactical problems/independent reference answers, fixing
acceptable move sets and their basis before candidate runs; disputed answers are
separate, never revised to favor a result. Primary development metric is explicit
tactical error rate with paired candidate-correct/baseline-wrong and reverse
counts. Equally acceptable different moves imply no gain. Incomplete search is
a separate execution failure. Record nodes/time as costs. Then run short games
without a pass-all gate or searching new problems until a difference appears.
Do not build a new problem generator. Dot's local search numbers were Agent
reports, not independently reproduced. Raw receipts/reads are ignored locally;
thread: https://nanomelon.slack.com/archives/C0C6L21UU20/p1791263068910849

The implemented comparison is documented in CHESS_DEVELOPMENT.md. Original
reference answers may be nonexhaustive: report agreement, not an asserted
tactical error rate, until a concrete error has supporting evidence. Keep the
original answer sets fixed; bounded independent child scores/actual games can
diagnose errors without turning every case into a certificate. One result file
and the existing common serializer suffice; raw local histories remain preserved.

On Windows, do not hold a large active JSON report open with `Get-Content`
while its producer uses atomic replacement. An observed long read interrupted
a game with WinError5; the previous frontier survived. Monitor producer stdout
and read completed reports, or use a reader explicitly sharing delete access.
Keep an interrupted sample distinct from a capped unfinished game; preserve the
old report and continue untouched declared cells, without silently rerunning it.

## Finish and limits

Before a final research reply use `session finish --reason REASON --evidence REF`.
Normal reasons: safe_checkpoint, no_viable_action; refused before60 minutes,
without a research stage, or without a valid memo reserve. After60 minutes
continue effective work toward90 and use a safe checkpoint. no_viable_action
needs fresh substantive review of two alternatives; supply `--alternative Q`
twice, matching distinct fresh research checkpoint questions. Old stop notes
are not proof. Resumed segments need fresh research, not an old stage plus idle time.
Early reasons: user_stop, user_decision, tool_limit, quota_limit, runtime_limit,
scientific_complete. Evidence must identify the actual instruction/failure or
necessary human choice; lack of a model/formula is not user_decision.
User stop takes precedence and requires no further research or memo preparation.
After finish copy status/start/reason into compact memo; aborted turns retain
active state. Publish/docs/consultation completion cannot end a segment.
Rejected finish or bypass followed by a final reply is a workflow failure.

The helper is receipts/structural validation, not a model, task runner, Goal,
scheduler, lease manager or auto-restart loop. It cannot prevent an App/model
exit, prove checkpoint truth/usefulness or verify effective research duration.
Elapsed time plus one stage passes only the mechanical duration gate, not the
acceptance test. No waiting or fabrication to achieve60 minutes.

## Acceptance and delivery

The first3 NORMAL segments after this rebuild have now been observed and
reviewed below. session_receipts.json retains at most3 summaries; session.json retains
the current/last segment. Inspect actual phase chains, elapsed time and evidence
for effective research. A short hard-blocked turn is recorded separately, not
a duration pass. A two-minute voluntary exit fails; diagnose the execution
break instead of relabelling it or writing retroactive justifications.
Pre-rebuild34-minute and80-second failures remain historical evidence in
docs/archive/continuation_before_20261004; they are not new-policy successes.

### Duration-policy acceptance

Observed3/3 normal segments after the rebuild with actual chain review. This is
an execution observation, not an App uptime guarantee or proof from a validator.
First segment2c26a558-2026-48ae-bfe2-473ec51eac31 ran from
2026-10-04T08:24:25.387003+00:00 to2026-10-04T09:45:44.571061+00:00:
81.320 minutes elapsed, eight research stages, normal safe_checkpoint ending.
Compaction resumed the same ID/start and later produced fresh research.

Quality review: the actual chain progressed from coupled-capture assumptions,
typed incidence and joint motifs to public replacement/signed-exposure controls,
exact leaf-choice/independent-label audit, finite owned-mode construction,
anonymous-hand arithmetic, ten ordered-effect controls and an H=2 closure
residual. Original memo tasks were completed and replaced with executable new
context/residual/certificate tasks. Publication was followed by a new research
stage, not final reply. No idle wait, extra worker, Goal or enlarged failed
experiment supplied the duration.81 relevant checks pass; five raw diagnostic
reports retain matching43 pinned input hashes. Scientific objective remains OPEN.

Evidence: docs/research/LOCAL_MAINLINE.md, FINITE_RESOURCE_LIFETIME_PROPOSAL.md,
OWNED_TAG_TRACE_RESULTS.md and the ignored local session receipt. Finish passed
its mechanical gate; this separate review evaluates the chain's content.
No early-ending claim was needed. Remaining future observations should check
actual continuation, especially after soft blocks, without repeating this sample
as additional acceptance or claiming that short exits can no longer happen.

Second segment5c0ad4a7-360d-4306-81b0-28ce02d6fc0b ran
2026-10-04T09:48:28.084939+00:00 to2026-10-04T10:52:37.541112+00:00:
64.158 minutes elapsed, nine research stages, normal safe_checkpoint ending.
Compaction resumed its original ID/start. Original memo's resource-context,
closure and pure-certificate tasks completed before replacement with new tasks.
Quality review: resource guards/proposals -> frozen root feasibility and specific
Pawn-table correction -> actual H2 paths/conditional rewards -> scoped origin/
custody controls and preserved partial-report failure -> DTM guard arithmetic ->
Queen rule equivalence -> direct-service tower/precision -> post-publication
held structural bound.81 relevant checks pass; four raw reports42 pinned inputs
match. Failed metadata lookup and missing original Chess numerical rows remain
explicit limitations; no completed Chess rerun was used to hide that failure.
No idle wait, Goal, worker or enlarged failed experiment supplied this duration.
End reason is elapsed safe checkpoint, not memo completion, dot reply or Git.
Evidence: LOCAL_MAINLINE.md, OWNED_H2_PATH_RESULTS.md,
DIRECT_FINITE_SERVICE_CONSTRUCTION.md and HELD_H2_STRUCTURAL_BOUND.md; ignored
session receipt records the actual time. Scientific objective remains OPEN;
the third observation below completes this limited three-segment acceptance.

Third segment f39424da-8a20-4061-a687-7fd2a5b63960 ran
2026-10-04T11:05:42.313726+00:00 to2026-10-04T12:06:07.428573+00:00:
60.419 minutes elapsed,12 research stages, safe_checkpoint. Actual chain:
held stratification/board covariance caveat -> decision-sensitive exact boxes ->
origin/castling scope and preserved final-write failure -> source metadata and
full-state request -> bounded actual independent table/parser acquisition ->
complete legal/terminal probes -> full-selector selected-child comparisons ->
H2 custody depletion -> independently specified two-victim root preflight ->
positive native-board bounds -> fixed-budget prospective direct pilot ->
post-publication tie sensitivity.100 relevant checks pass; eight reports74 local
pinned input hashes match. External source files remain ignored and verified.
Dot's full reply was reread/reconciled without routine acknowledgement; actual
Slack emphasis rendering friction was repaired with regression coverage.
Original memo tasks completed, then were replaced with executable pilot,
reserved-use and held/control tasks. No Goal, worker, expanded budget, idle wait
or unchanged empirical rerun supplied the duration. A finish attempted about
seven seconds before60 was rejected; work continued with stored-table tie
analysis before the accepted finish, rather than bypassing the gate. One
PowerShell inline verification failed quoting and was corrected with a literal
multiline Python input; the exact counterfactual margins[0,1,0,1] were verified.
No future App uptime or permanent prevention of short exits is claimed.
Scientific objective remains OPEN; prospective direct pilot has not executed.
Evidence: SMALL_CERTIFICATE_FIRST_PROBE_RESULTS.md,
SMALL_SELECTOR_DIAGNOSTIC_RESULTS.md, TWO_VICTIM_PREFLIGHT_RESULTS.md,
TWO_VICTIM_FIRST_REWARD_BOUND.md, TWO_VICTIM_DIRECT_INTERVAL_PILOT.md and the
ignored local segment receipt. The separate review, not elapsed time alone,
qualifies these three observations; keep observing future normal continuations.

One native four-hour heartbeat, same chat, preserving notification intent.
User changed cadence on2026-10-04: Asia/Tokyo02:00,06:00,10:00,14:00,18:00,22:00.
The existing automation was updated through the native tool, not duplicated;
daily10:00 consultation stays in that same schedule. Historical two-hour
receipts remain evidence of the earlier configuration, not current policy.
Daily10:00 Tokyo substantive dot window, no mandatory external response or
routine acknowledgement. Standing Slack authorization and complete-reply/
uncertain-send handling: SLACK_WORKFLOW.md. Standing authorization includes
Agent judgment on deliberate resend/recontact, reaffirmed2026-10-05. Reconcile
delivery first, record evidence and duplicate risk, keep known-root followups
in that thread; no per-attempt user approval, automatic loop or ledger reset.
Explicit stop persists flags;
Agent pauses heartbeat/cancels dot monitoring, no scheduled automatic resume.
Transport/local Agent allowance boundaries remain in advisor.json.
Inspect outgoing diffs, run relevant tests, publish and verify origin/sandbox.
Recovery/isolation evidence remains REBUILD_20261003.md; never import old
App databases, credentials, Goals or retired queues. Do not touch other projects.
