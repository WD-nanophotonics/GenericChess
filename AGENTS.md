# GenericChess local research policy

This is the sole active policy; user instructions take precedence. One local
Agent works on sandbox in this checkout. Never touch alphasho, its audits,
tasks or other projects. No extra Agents, Work/Codex delegates or heavy jobs.

User2026-10-11 explicitly authorizes a user-established auxiliary validation
Agent. This scoped exception does not authorize automatic spawning/delegation.
The primary Agent remains the sole writer/publisher of sandbox in this checkout;
the auxiliary validator uses its own checkout, branch and evidence directory,
reads pinned source and returns independent validation results. It does not edit
primary state, stop/session/memo files, engine defaults or UI, or publish sandbox.
Assignment boundaries and shared-account Slack identity limits are specified in
docs/operations/AUXILIARY_VALIDATION.md. User confirmed 开发辅助=DEV_AUX on sidemission, sharing the Slack account;
PRIMARY_SANDBOX remains the primary. Use these simple fixed routing IDs without
per-message challenges or extra identity gates. Shared-account labels are not
cryptographic process authentication. Other isolation/safety rules stay.
User2026-10-11 also requires a remotely readable collaboration record. At each
completed segment update docs/operations/COLLABORATION_LOG.md with both Agents'
contributions, coordination, disagreements/corrections, adoption reasoning,
efficiency evidence/limits and unresolved issues; publish reviewed Agent-only
summaries to sandbox and give Dot a fixed-revision link. Exclude raw Slack,
account/private inputs. This is a short evidence summary, not extra approval,
identity challenges or a requirement to wake the auxiliary for routine replies.


At every start, restart, heartbeat and after compaction, FIRST read
.local_agent/NEXT_WORK.md in full, then this file, LOCAL_MAINLINE.md and
rollout/advisor/slack stop flags. Never clear a user stop. A missing/stale memo
is rebuilt from evidence before research; checking flags never permits clearing them.
Memo has at most20 lines/2KiB UTF-8, with State, Segment, Main, Backup1, Backup2,
Evidence fields. Each task is question | immediate first action | expected
evidence | done condition. Overwrite completed/stale tasks; no memo diary/archive.
It is revisable resume memory, not an approval queue or work-volume limit.

Normal manual starts AND heartbeat continuations are research segments aiming
for60-90 minutes of effective work, without Goal. Do not relabel a heartbeat
as inspection-only to avoid research. Explicit bounded user configuration,
explanation/review requests are not duration samples. Before research call
session start; session.json owns the ID/start time. Resume active segments
after interruption/compaction without resetting the clock or creating writers.
Execute the Main task immediately. At each milestone validate, assess mainline
impact, record a session checkpoint, then SELECT AND BEGIN the next useful step.
Tests, docs, memo, consultation, commits and publication are checkpoints.

Missing formulas, negative results, a restricted old route or dot silence are
SOFT blockages: switch to a backup, or actively search new primary literature,
design a falsifiable hypothesis, derive a relevant result or run a bounded
feasibility check. Hypothesis construction need not first prove exact WDL
calibration or rules uniquely choosing a context law. State assumptions and
distinguish semantics, approximation and independent deployment evidence.
Old failures restrict tested claims, not entire fields. Revisit a failed route
only with a changed premise and a specific decision-changing check; no unchanged
reruns, exposed-label fitting, human-price tuning or Xiangqi human-holdout reads.
Preserve Chess/Shogi/Xiangqi semantic boundaries and frozen comparison records.
User2026-10-06 prioritizes information per cost, not universal compute cutoffs.
Development time/count limits are cost checkpoints; within existing permission,
continue a bounded, interruptible batch when its possible outcomes can change a
specific decision. Briefly record the unknown, decision-changing outcomes and
incremental cost; count engineering/token overhead too, without approval queues.
Permissions, machine safety and declared fair-comparison conditions remain hard
boundaries. Keep old cap failures intact; added development never restores
unexposed validation status. Compare methods under the same resource condition
or report resource/result curves. No result-driven extension of frozen tests,
runaway jobs, extra fees/workers or access bypass. See LOCAL_AGENT.md Budget.

Current priority, updated by the user-requested2026-10-10 handoff review:
search capability comparison and bottleneck attribution first. Compare supported
generic search/backend, minimal alpha-beta with Chess/Shogi specialized rules,
and mature engines; use the same minimal AB on generic rules as a thin attribution
bridge. Separate rule execution, repeated scheduling, representation costs,
algorithm optimizations and budget completion. Fixed primitive cost, defined
work counts and equal-time decision usefulness are distinct evidence. Record
actual backend/fallback and evaluation differences; unaligned mature engines are
overall references, not material-only search controls. Small predeclared positions
precede large games/Elo. Infrastructure gaps that impede these judgments should
be repaired and their effects measured, not deferred merely as engineering.
Price/statistical averaging and small learning routes remain later goals;
context dependence alone does not refute a fixed vector averaged under an
explicit play distribution. No timing, stop, publication or long-run rule changes.

Retained long-term research, clarified by user2026-10-07 and verified2026-10-08,
has two lines: rule-only generic piece-value generation, cross-game ordering/
ratio comparisons and explanation of bias; and efficient/stable search with a
generic interface on unfamiliar rules (familiar-piece mixtures, recombined
mechanics, existing-generator random rules with simple playability filtering).
Games are secondary price-hole diagnostics, not a player-strength optimization
goal. Do not keep adding positional patches or chasing classical/engine Elo.
Static rule-derived tables remain candidates and cheap baselines, not a required
predecessor to every evaluation route. Learning/frozen constants and small state
interaction evaluators may receive literature and low-cost feasibility review.
User2026-10-09 authorizes appropriate small local training without per-run user
approval. Before any single project run expected to exceed one hour, consult dot
and obtain its assessment that the run is genuinely necessary; record the
decision question, estimated cost and cheaper alternatives. This applies to
training and other project runs, not the60-90minute Agent research segment.
If confirmation is pending, continue independent shorter work. Do not split a
long run artificially to evade consultation. Preserve stop flags, fair comparisons,
data boundaries and machine safety; no extra workers, fees or uncontrolled jobs.
This permission does not revive old phase gates or authorize large training.
Generic means the project's complete generated rule domain across search, state,
evaluation and learning: preserve promotion, drops, auxiliary and relevant
history semantics. Scoped prototypes are allowed with explicit exclusions, not
substitutes for that target. Mechanical rule compilation is allowed; manually
separate game-specific solutions do not establish generality.
Choose evaluation routes by useful decisions per cost, with behavioral ablation
and stated limits; complete explanation or exact probabilities are not admission
requirements. Finish optional precision work only if its possible outcomes
change a specific next choice. Current route comparison: EVALUATION_ROUTES.md.
Use existing frozen outputs and search entries; expose one decision-changing
mechanism or interface issue at a time. Human-reference agreement is descriptive
validation, never proof of a universal optimum or permission to fit the formula.
Limited tactical/game measurements need not first
have exact WDL, all-defense proofs or independent holdout status; label scope.
Preserve legality/semantic checks and fair conditions. Broader proofs address
observed failures or concrete uses. Advisor suggestions are not a branch backlog:
choose the decision-changing objection and one next action, not every risk.

Static generation must preserve supported semantic equivalence. Check stability
under behaviorally small capability changes and consistency as rules approach
the same finite-board behavior; textual edit size is not behavioral size.
Report raw opportunity, normalization, rounding/clipping and unsupported scope
separately. Missing NNUE/position modeling cannot explain representation defects.
Quantity changes and genuinely splitting one actor into two are empirical
relations, not assumed linearity/conservation. Limited coalition modeling does
not cancel equivalent-rule consistency. Keep these checks finite and motivated.
Separate semantic correctness, price sensitivity and search execution cost.
Price comparisons fix attack authority/search conditions and distinguish leaf
prices from ordering prices. Changed choices or broken ties alone are not gains.

Before60 minutes, a normal/no-next-action finish is forbidden. Early finish
requires explicit user stop, actual tool/quota/runtime limit, a genuinely
necessary user decision, or evidence-supported scientific completion. A missing
research hypothesis is not a user-decision blocker. After60 minutes continue
an effective line toward90, then end at a safe checkpoint. Do not pad time
with idle waiting, old conclusions, irrelevant proofs or infrastructure.
Before final research reply call session finish with evidence; rejection means
continue, not bypass. No-next-action after60 requires fresh examination of at
least two alternatives, not reuse of an old no-work note. Refill memo with
executable tasks before normal finish. Record actual time and ending cause.
The validator checks structure/time only; bypass or rejected-finish exit is a
workflow failure, not a compliant inspection. App uptime is not guaranteed.

Agent and dot are near-peer research partners; user instructions win. Record
adopt/defer/reject reasoning. Dot is not a work issuer or publication gate.
Slack NanoMelon #generic-chess C0C6L21UU20 is the sole consultation channel.
Standing user authorization permits connected-account sends to that channel
and its threads across turns/restarts until revoked; explicit stop suspends
sending. Send only concrete useful questions/evidence, not routine acknowledgements.
Use consult/consult-status/reconcile; immutable IDs/hashes/root ts bind requests.
Verified account identity, not TYPE/ID, authenticates the sender. Dot shares
the current account. Paths do not give dot local access; attach bounded evidence.
At every recovery and useful consultation checkpoint read channel new roots
as well as relevant threads, with pagination/coverage recorded; do not inspect
only pending requests. User2026-10-10 explicitly requires: whenever the user
asks to ask Slack, obtain new requirements or inquire about direction, open a
NEW THREAD with TYPE=AGENT_REQUEST and a fresh REQUEST_ID. Never send that
inquiry as a follow-up, reuse an old thread, or use AGENT_FOLLOWUP. This overrides
the earlier compatible same-thread renewal convention for these user requests.
Agent-initiated evidence-based review of an existing technical question may
use AGENT_REQUEST plus original ID/unique FOLLOWUP_ID in its existing thread;
it is not a template for explicit user-directed Slack inquiries.
EVIDENCE/RESULT are informational. Advisor-origin new threads
are explicitly associated as supplements, never rebound as the original root.
Keep per-followup pending/received/evaluated/applied/deferred records and exact
message versions. Delivery is not response or adoption; missed events and
latency are observable limitations, not guaranteed wake/reply promises.
Read all posts/pages and preserve raw output before reconcile/adoption; completed
requests can get supplements. Standing authorization also covers Agent judgment
about resend/recontact, reaffirmed2026-10-05; no per-attempt user approval is
needed. User2026-10-08 explicitly authorizes sends and repeated content to this
channel at Agent discretion; local retry flags are not permission denials.
Reconcile first and record the delivery evidence, purpose and duplicate
risk before any deliberate retry. Missing search matches alone are not proof
of nondelivery. For a known root use its thread, never another channel; a mere
silent dot is not a reason for routine repeats. Preserve IDs/hashes/receipts,
never reset the ledger or run automatic retry loops. See SLACK_WORKFLOW.md.
No self-reply loops, automatic re-execution or additional workers.

Daily10:00 Asia/Tokyo is the main substantive dot window; skip empty/duplicate
questions and missed-day catchup. Work independently otherwise; consult as needed.
Read/wait briefly at useful checkpoints and continue independent work. The sole
native90-minute heartbeat resumes this chat without overlap or a second writer.
Daily10:00 Asia/Tokyo stays the main consultation window; if no turn is active,
the first heartbeat after10:00 handles that day once, without missed-day catchup
or another task. Existing active research never starts a second writer.
No Windows scheduler, Goal, ownership/Supervisor policy, Chat approval, Courier,
native Chat send or Socket Mode prerequisite. Historical snapshots are evidence.
Explicit user stop suspends consultation/heartbeat and cancels dot monitoring;
restart never clears stopped state. Local Agent/heartbeat use normal allowance;
dot/transport must not delegate workers. Quota evidence is in advisor.json.

Git is version control/final delivery, not mandatory communication. Inspect
outgoing diffs and relevant tests before publish; verify full origin/sandbox SHA.
User2026-10-07 grants standing publication authorization for this project's
Agent-generated code, research results and evidence, including the pending
backlog. At every completed work segment commit and sync these to origin/sandbox
so dot can inspect actual changes, without per-push confirmation. Exclude user-
authored/private input data, raw Slack/account records and credentials, including
inside archives and outgoing history. Authorization persists until revoked;
explicit project stop suspends publication. Old held-publication records are
historical status, not an active gate. Review and test; report push failures and
verify the exact remote SHA. Never claim a local commit was published.
Use existing generic-chess-local.cmd publish --tests <relevant pytest targets>;
the repository hook requires this tested entry for sandbox pushes.
Master promotion is tested fast-forward only; never force-push. Report truthfully.
Notify only meaningful results, failures or required decisions. Scientific
completion requires the evidence in LOCAL_MAINLINE.md, not a phase/turn boundary.
Operations: docs/operations/LOCAL_AGENT.md and SLACK_WORKFLOW.md.
Recovery: docs/operations/REBUILD_20261003.md.

Repository layers and isolated historical recovery: docs/operations/REPOSITORY_LAYOUT.md.
Default pytest covers the four active test layers; old receipt tests are history.

## User update 2026-10-11: ordinary concurrency

Ordinary concurrent projects and Agents on this computer are allowed. Do not
request CPU quiet windows, pause independent work, or classify ordinary overlap
as a collaboration failure. Protect separate checkout files and running computation
state; act on direct boundary violations or damage. Record relevant measurement
conditions as interpretation limits without adding coordination gates or automatic
reruns. This user instruction supersedes earlier CPU-solitude wording.


## User update2026-10-12: diagnosed blockers and schedule termination

This applies to every GenericChess Agent, including PRIMARY_SANDBOX and DEV_AUX.
A blocked Agent must actively diagnose the root cause, assess severity and
necessary permissions, and solve recoverable technical/entry problems itself.
An undiagnosed error, missing entry, stale failure, silent advisor or missing
next idea is not a severe blocker and does not justify ending before60minutes.
Repeated heartbeat checks of the same limitation, memo edits, mocks and side
results cannot substitute for fixing the obstacle to the requested experiment.
Only an evidence-backed serious problem that the Agent cannot solve without
necessary user intervention permits the blocked ending: first report the concrete
cause, attempted remedies, indispensable user action and saved state, then pause
that Agent's existing schedule/heartbeat and consultation. Do not keep recurring
empty runs, create replacements or auto-resume. Explicit user stops still win.
The session validator accepting an exception is not evidence that it was justified.
Each Agent owns its state and schedule; communicate the project-wide rule through
the authorized channel, never write another checkout. A resolved entry keeps its
normal research cadence. Preserve historical failures and mark mistaken endings
as mistakes rather than rewriting them into compliant runs.

# DEV_AUX current scope —2026-10-15 segment52

ScienceOPEN; sidemissiononly; manualresearch session52, heartbeatPAUSED.
ActualWDLlearning cheap, stablehumanprice/transfer NOT established.
FreshRNBnative-opponent replicate .03125 CI touch0; new4RNPpromotion .0859375 positive.
Twoactualrandominitialpaths TRAINimprove but bothDEVbelowunit .015625; endpoint128trajectoriesidentical.
CompleteD3bothTRAIN learnR1440/P360, matchedDEV .1328125positive, workdifferent; all8638/51095values independentlychecked.
8cold64transfer negativeuncertain; NEW8candidate4096learnR=P1440, DEV .0234375uncertain,strongop0.
AlignedEval/native/captureprices work, fixed8pricegain.015625uncertain; pairedinteractionscross0.
Currentbare/singleN/B4/8 ruleDrawproof complete; futurecostforecast notwallgain.
32coldquerypairs rawidentical, duplicateSclear64to32; clockzero timingclaimrejected.
84701newNativego14656newepisodes1832perft; source/phase/clockfailurespreserved+fixed.
Nextnewdriver explicitrule/node/table keys+oneclear+stockproof; freshalignedlearning/opmix, noDEVfit.
No product/default/UI/primary writes orfullChess/Shogi/generateddomain claim.
Evidence:SEGMENT_20261015_52.md,COST/QA/FAILURES/SESSION/archives52,1674/1679/1687/1694/1700/1711/1714/1717/1718.
