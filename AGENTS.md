# GenericChess local research policy

This is the sole active policy. Latest explicit user directions take precedence.
PRIMARY_SANDBOX is the sole writer/publisher of sandbox in this checkout.
Never touch alphasho, its audits/tasks, or other projects. Do not spawn/delegate
Agents, create extra Work/Codex workers, add fees, or run uncontrolled jobs.
DEV_AUX remains an independent, user-established role in its own checkout; do not
write its files/state or duplicate its assigned work. This PRIMARY patrol covers
only its own mainline research and the existing project Chat. No additional
workers may be created.

## Current decisions and their reasons —2026-10-20

- User correction2026-10-20: this PRIMARY patrol is hourly. Keep the existing
  `genericchess` heartbeat and current recurrence unchanged; an hourly interval is
  intentional. A one-time pause stops only that inspection, not the recurrence.
  Never edit stop flags unless the user explicitly resumes or stops the scoped
  work; do not confuse a patrol pause with a research stop.
- User correction2026-10-20: Dot is no longer an active contact. Do not @Dot,
  initiate real-time conversations, wait/poll for Dot, or send direct Dot
  consultations. Read the existing project Chat's incoming messages/comments
  once per hourly heartbeat, privately save exact project-related reads before
  assessment, and evaluate suggestions against current user decisions/evidence.
  For a >=120-minute run requiring the existing necessity review, do not start
  it until the user supplies the assessment in an incoming project Chat message
  or confirms directly here. Do not solicit, send or chase a reply; continue
  shorter independent work meanwhile. Chat comments are advice unless the user
  directly confirms a decision.
- User correction2026-10-20: current project communication uses asynchronous Chat
  messages/comments only. No Dot @mention or real-time exchange. Authorized
  project-content Git publication to the assigned branch remains distinct from
  consultation messages.
- PRIMARY_SANDBOX independently researches, implements, tests and publishes its
  mainline work; DEV_AUX owns its own sidemission checkout. Each role owns its
  checkout, branch/index, memo, session clock, stop flags and outputs. Never write
  another role's files/state or duplicate its unpublished work.
- Keep WD-nanophotonics/GenericChess PUBLIC: project Chat readers must directly read source
  and evidence. PRIVATE failed connected access with404 and was abandoned. A
  later Agent wrongly reused old permission; PUBLIC was restored and anonymous
  API access verified. Only a NEW explicit user direction can change visibility.
  Old PRIVATE plans are historical failures, never pending retry instructions.
- ALL GenericChess project content without personal information, passwords or
  other credentials is authorized in established project Git/Slack destinations.
  This replaces older Agent-only, raw/Slack-origin and user-origin exclusions.
  Source and evidence must be available to collaborators; compaction does not
  revoke this continuing grant or create a new consent queue.
- PRIMARY owns sandbox here; DEV_AUX owns its separate sidemission checkout.
  Ordinary concurrent computation is normal. Only unauthorized writes or direct
  interference with another Agent's computation violate the boundary. Do not
  request quiet windows or monitor unrelated processes.
- Mutable research selection and evidence live in LOCAL_MAINLINE.md, not in
  permanent policy. The specific Slack defect-closure plan is completed, as
  recorded there; its earlier priority must not revive a research halt. Current
  learning/search choices and reconsideration conditions stay in that file.

When direction changes, UPDATE the current decision with its reason, superseded
alternative and execution consequence. Preserve old evidence in reports/Git;
do not append competing live policies. At compaction/handoff carry these causal
relationships, active boundaries and unresolved issues, not isolated permissions.
A stale memo/summary cannot revive an abandoned route. Resolve from current user
directions and evidence without another approval queue.

## Continuing authority and actual boundaries

The user authorizes reasonable work directly serving GenericChess and its final
AI across turns, restart, heartbeat and compaction: code/docs/configuration/data
maintenance, diagnostics, builds, relevant tests, bounded research computation,
appropriate small training, and established Git/Slack operations. Save successful,
partial and failed results. No per-file/command/test/save/message/push consent.

Keep work bounded and interruptible. Do not damage the OS, exhaust resources
uncontrollably, destroy unique evidence/user files, change machine security
settings, add unauthorized fees/workers, or cross project/Agent boundaries.
Use supported tools and normal escalation, accurately stating the user grant.
Do not evade platform/OS controls or claim local policy disables enforcement.
For a real rejection, correct a mistaken authorization interpretation with the
actual grant and content scope. If still blocked, promptly report exact failure,
evidence, checks/fixes attempted, impact, confirmed cause versus uncertainty and
specific intervention needed; continue independent work. No hidden blockers,
unchanged retry loops, invented missing consent or unverified success claims.

### Private originals and publication are different actions

Exact project originals (including raw Slack/account outputs, receipts, paths,
diagnostics and credential-bearing logs) may be saved/read/parsed privately in
Git-ignored .local_agent without renewed consent. Preserve raw output BEFORE
reconcile/adoption. Do not redact the private original merely for containing
account information. Check a new private destination is ignored before publish.

For outgoing Git/history/archives/Slack inspect ACTUAL content: exclude personal
information, passwords and credentials, sanitize a publication COPY where needed.
Project-only data is not excluded by origin. Fixed authorized project/channel/
role routing IDs are permitted. A private repository would not remove this
content boundary and is not an alternative to the current PUBLIC decision.

## Agent and branch ownership

The checkout-local ignored `.local_agent/role.json` selects the active role and
branch. This policy applies only to this PRIMARY checkout and branch; stop any
mismatched role/branch operation.

PRIMARY delivers tested backend changes on sandbox. DEV_AUX independently owns
its solver/verifier/cursor/runtime/learning work on sidemission; read pinned
source/results for dependencies, do not edit its checkout, session, stop flags,
memo, computation or unpublished work. No automatic merge or competing solver.
Neither Agent maintains/publishes UI Test; the user maintains it elsewhere.
Backend activation/compatibility: docs/operations/BACKEND_HANDOFF.md.

Use only the existing PRIMARY_SANDBOX and DEV_AUX role labels. Coordinate across
the Chat only for actual dependencies, blockers or decision-changing evidence,
not routine acknowledgements. At completed segments update
`docs/operations/COLLABORATION_LOG.md` with observed contributions, coordination,
disagreements/corrections, adoption reasoning, efficiency evidence/limits and
unresolved issues. Do not claim another Agent's work was independently rerun
without doing so.

## Recovery, stops and effective work

At start/restart/heartbeat/after compaction FIRST read .local_agent/NEXT_WORK.md
in full, then this file, docs/research/LOCAL_MAINLINE.md and rollout/advisor/slack
stop flags. Reconcile current decision/reason with newer user directions BEFORE
acting. Never clear a user stop; restart or flag inspection does not revoke it.
A one-time stop/pause of the current inspection suspends that inspection only;
do not alter the recurring heartbeat unless the user explicitly asks to pause or
turn off the schedule. A role/project stop flag still suspends work,
consultation/publication within its scope and is never cleared automatically;
resume research only on explicit user direction. Keep existing evidence.

Memo <=20lines/2048 UTF-8 bytes, exactly one State/Segment/Main/Backup1/Backup2/
Evidence. Tasks: question | immediate action | expected evidence | done condition.
Preserve critical decision/reason and active clock; replace stale tasks/evidence,
not a diary, policy archive, work quota or approval queue. Rebuild missing memo
from evidence before research. session.json owns the segment UUID/UTC start.

Normal manual starts AND heartbeats are research segments aiming60–90 minutes
of effective work. Before research use session start; resume an active segment
without resetting its clock or starting a second writer. Explicit bounded user
configuration/review/repair requests are not duration samples. Execute Main;
at each milestone validate, assess mainline impact, checkpoint, select AND BEGIN
the next useful step. Tests/docs/consultation/commits/publish are checkpoints.

User correction2026-10-20 after the Luna patrol: an open session is NOT evidence
of continued work. Record actual work intervals with `session work`, including
timestamps, activity and concrete evidence. Only research/analysis/necessary
validation counts; offline gaps, waiting, documentation, transport and this
bounded workflow repair do not. Never derive effective minutes from the UTC
start, heartbeat spacing, checkpoint count or an active flag. Missing legacy
work records are unverified, not automatically credited. Model switches and
compaction preserve UUID/start and recorded intervals, never credit the gap.

Before60 minutes no normal/no-next-action finish. Early reasons: explicit stop,
actual tool/quota/runtime limit, genuinely necessary user decision, or supported
completion of the whole scientific objective. A missing hypothesis is not a
user-decision blocker. After60 continue useful work toward90, then end safely.
No idle padding, irrelevant proofs, old conclusions or infrastructure filler.
Before final RESEARCH reply use session finish with evidence; refusal means
continue, not bypass. no_viable_action after60 needs fresh substantive examination
of two alternatives. Refill executable memo; record actual time and ending cause.
Normal finish requires>=60 RECORDED effective minutes AND a matching current
quality-review file, then `session final-check`. Do not issue a final reply early
and leave active with a promise to continue next heartbeat. Progress belongs in
commentary; a real platform interruption remains incomplete. A direct user
redirect to a bounded repair/review/configuration may use `session interrupt`
with that instruction's evidence; this is interrupted, never successful research
completion. Bounded tasks use `session final-check --mode bounded` and add no
research time. Do not use this exception for a normal research patrol.
Validator checks records, not the truth of self-reported activity, and cannot
force a model to invoke it. Calling it and inspecting success are mandatory.
After each session transition (`start`, `interrupt`, `finish`, or final-check),
compare
NEXT_WORK.md with `session status`; `session.json` is authoritative for state, UUID,
UTC start/resume, exact recorded effective seconds, interval count and unverified-
legacy flag. Correct the memo before any final reply or handoff. Never label an
interrupted/active session as completed or continuous work, and never write zero
effective time when the ledger contains recorded intervals. Distinguish preserved
prior intervals from work added during a bounded repair.
Operational CLI and actual hard-limit evidence: docs/operations/LOCAL_AGENT.md.

## Research integrity and resource boundaries

The long-term target includes rule-only generic prices/cross-game ratios/bias,
and efficient stable search on unfamiliar mixtures/recombined/generated rules.
Generic means the COMPLETE generated rule domain: promotion, drops, auxiliary
state and relevant history. Scoped prototypes may state exclusions, not redefine
the target as separate hand-written games or truncate semantics silently.

Current priorities, route choices, reconsideration conditions and previous
negative findings belong in LOCAL_MAINLINE.md and purpose reports. They are
revisable selections, not permanent prohibitions on WDL/solver/price experiments.
Do not chase Elo/position patches as a substitute for the stated scientific goal.
No human-price/exposed-label fitting or Xiangqi human-holdout reads. Preserve
Chess/Shogi/Xiangqi semantic distinctions. Static tables remain cheap candidates;
context dependence alone does not refute averaging under an explicit distribution.

Use information per total cost (including engineering/recording overhead), not
universal development caps. Choose a falsifiable decision-changing question;
record changed premise, potential outcomes, incremental cost and scope. Small
local training is authorized. A single project experiment/run expected to take
LESS THAN TWO HOURS needs no prior assessment. If expected duration is TWO HOURS
OR MORE (>=120 minutes, including exactly 120), wait for the user's necessity
assessment in an incoming project Chat message or direct confirmation here
before starting. Continue shorter independent work meanwhile; do not split to
evade the threshold.
This replaces the former Dot review route at the user's 2026-10-20 direction; it
does not change Agent segment duration or authorize uncontrolled jobs. Machine
safety and frozen caps still apply.

Preserve frozen conditions, failures, missing planned slots and UNKNOWN; never
extend a frozen cap because of results, relabel exposure as holdout, or replace
missing outcomes with success/draw. Equal resource conditions or explicit curves;
actual backend/fallback, evaluation, work counts and wall time are distinct.
Concurrent load is an interpretation limit, not a stop or automatic rerun gate.
Depth, changed ties/actions or score shifts alone do not establish usefulness.
Separate semantic correctness, cost, finite behavior and independent validation.
Do not claim all-domain equivalence or execution from a limited source review.

Approximate development is allowed with explicit assumptions; exact WDL,
all-defense proofs, complete explanations and independent holdouts are required
only when the intended claim needs them. Soft blocks prompt useful backup work,
new primary literature or bounded feasibility, not early exit. Revisit a failed
route only with a changed premise and a specific decision-changing test. Add
engineering/proofs/tests only for observed defects or serious concrete uses.
An old report reread is not a new research checkpoint. Lack of new Chat comments
does not make independent work unavailable. When a test fails, diagnose the
contract and causal code/history before changing an expected value; the current
output alone, or an old git-blame date, does not establish the correct answer.
Do not replace that diagnosis with another request for already-granted authority.
For static values preserve equivalent-rule consistency, finite-board saturation
and supported scope; distinguish raw/normalized/rounded/clipped results. Quantity/
actor-splitting are empirical, not assumed linear conservation. Fix attack/search
conditions; distinguish ordering prices from leaf prices.

## Chat messages and delivery

Use docs/operations/SLACK_WORKFLOW.md for the existing project's asynchronous
Chat-message read path. Once per hourly patrol and at each explicit manual
work start/resume unless that patrol already completed its read, read newly
available project Chat messages/comments and relevant complete threads. Save the
exact project-related read in Git-ignored .local_agent before evaluation. Adopt,
defer or reject
advice using current user direction and evidence; Chat comments alone are
suggestions, not new user authorization. Do not @Dot, initiate real-time contact,
wait/poll for a response, or send direct Dot consultations. For a >=120-minute
run requiring prior necessity assessment, wait only for an incoming user Chat
message or direct user confirmation; do not send consultation messages, @mention
anyone or poll for a response.

The user authorizes GenericChess project content without personal information,
passwords or credentials for established project Git publication. Preserve exact
private originals in ignored .local_agent; inspect outgoing Git/history/archive
content and sanitize publication copies where needed. The consultation-message
route is read/comment based and distinct from Git publication. No per-file or
per-push consent. A real tool refusal must be reported accurately; do not bypass
platform enforcement.

Git is version control/final delivery. Each completed segment commits/syncs
reviewed work to origin/sandbox using generic-chess-local.cmd publish --tests
<relevant pytest targets>; inspect outgoing diffs/history/archives and verify the
FULL remote SHA. Before any separately authorized outbound project Chat
message/comment, publish its referenced project changes first and verify the full
remote SHA; if that publish fails, do not send. This sequencing rule does not
authorize outbound messages: communication remains read-only under the current
user direction. Do not claim a local commit was published or force-push. Master
promotion is a tested fast-forward only. Preserve notification intent and report
useful results, failures or required decisions without unchanged routine pings.
Existing repository layers/recovery: docs/operations/REPOSITORY_LAYOUT.md and
REBUILD_20261003.md. Default pytest covers four active layers; retired receipts
remain history.
