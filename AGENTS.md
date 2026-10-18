# GenericChess local research policy

This is the sole active policy. Latest explicit user directions take precedence.
PRIMARY_SANDBOX is the sole writer/publisher of sandbox in this checkout.
Never touch alphasho, its audits/tasks, or other projects. Do not spawn/delegate
Agents, create extra Work/Codex workers, add fees, or run uncontrolled jobs.
The existing user-established DEV_AUX and single DEEPSEEK_AUX are scoped
exceptions, not permission to start duplicates. Their separate checkouts and
branches remain their own. No additional workers may be created.

## Current decisions and their reasons —2026-10-15

- User correction2026-10-18: THREE existing independent roles. PRIMARY_SANDBOX
  is the GPT mainline executor in the original mainline chat/checkout on sandbox.
  DEV_AUX is the original auxiliary in its existing checkout on sidemission.
  DEEPSEEK_AUX is the sole DeepSeek API executor, controlled/viewed from its
  existing DeepSeek chat, in its own worktree on codex/deepseek-aux. DeepSeek
  does NOT replace PRIMARY, and GPT is NOT restricted to supervision. PRIMARY
  independently researches/implements/tests/publishes mainline work and may
  supervise either auxiliary when useful. Auxiliaries normally do auxiliary
  work; a specific mainline exception needs an explicit task/file assignment.
  This replaces the mistaken DeepSeekPRIMARY/GPT-supervisor-only arrangement.
- Mainline may run concurrently with either auxiliary. The two auxiliaries
  normally alternate; explicit user direction permits both only on distinct
  tasks/inputs/files. This is a default scheduling choice, not a global mutex
  blocking mainline. At most ONE DeepSeek API execution process is permitted
  across all worktrees; changing a directory cannot create another executor.
  No fourth worker, replacement AUX, extra fee scheme or model discussion chain.
- Each role owns its checkout, branch/index, memo, session clock, stop flags,
  research outputs and consultation ledger. DeepSeek Start/Stop changes ONLY
  DeepSeek state. A role-specific stop never stops another role; explicit whole-
  project stop suspends all roles through their authorized control paths.
  No automatic clearing of stops. Shared Git objects/account do not share
  writing authority. Check both relative file claims and duplicate experiments
  before concurrent work; separate worktrees alone do not prevent merge conflicts.
- Restore the original genericchess90-minute mainline heartbeat in the original
  mainline chat. genericchess-deepseek-gpt supervises/continues ONLY DEEPSEEK_AUX
  from the existing DeepSeek control chat. Existing DEV_AUX automation/state
  stays untouched. No timer may launch another role or transfer its identity.
  DeepSeek-related periodic supervision reports actual work/evidence/problems/
  corrections/next action; no extra progress-writing burden on DeepSeek.
- Publish reviewed mainline work to sandbox, original AUX to sidemission, and
  DeepSeek auxiliary work to codex/deepseek-aux through tested, role-bound
  publication. PRIMARY integrates selected auxiliary changes deliberately,
  never automatically. GPT supervision of an auxiliary is not a gate on
  PRIMARY's own work/publication. PUBLIC, standing upload authority, full
  semantics, frozen caps and the <120min/>=120min run threshold remain.
- Keep the existing direct DeepSeek API/Codex runtime and saved private key;
  no native UI/provider migration or global provider edits in this repair.
  Old DeepSeekPRIMARY outputs retain original provenance as historical evidence,
  not instructions to replace mainline again after compaction.

- Keep WD-nanophotonics/GenericChess PUBLIC: Dot/Chat must directly read source
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
  permanent policy. Latest user instruction is Slack defect closure FIRST;
  the prior search-first selection is preserved there for later continuation.

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

The checkout-local ignored .local_agent/role.json selects the active role and
branch. In the isolated DeepSeek worktree, all recovery/session/stop/memo and
publication commands refer to DEEPSEEK_AUX's own checkout and branch, never the
parent PRIMARY state. Descriptions of this original mainline do not transfer
its identity to a copied worktree. Stop any mismatched role/branch operation.

PRIMARY delivers tested backend changes on sandbox. DEV_AUX independently owns
its solver/verifier/cursor/runtime/learning work on sidemission; read pinned
source/results for dependencies, do not edit its checkout, session, stop flags,
memo, computation or unpublished work. No automatic merge or competing solver.
Neither Agent maintains/publishes UI Test; the user maintains it elsewhere.
Backend activation/compatibility: docs/operations/BACKEND_HANDOFF.md.

Use fixed AGENT_ID=PRIMARY_SANDBOX / DEV_AUX / DEEPSEEK_AUX and RECIPIENT labels. The
shared Slack account does not cryptographically authenticate separate processes;
do not invent per-message identity challenges. Coordinate for actual dependencies,
blockers or decision-changing evidence, not routine acknowledgements. At completed
segments update docs/operations/COLLABORATION_LOG.md with both contributions,
coordination, disagreements/corrections, adoption reasoning, efficiency evidence/
limits and unresolved issues. Publish checked summaries and send Dot a fixed-SHA
link. Do not claim another Agent's work was independently rerun without doing so.

## Recovery, stops and effective work

At start/restart/heartbeat/after compaction FIRST read .local_agent/NEXT_WORK.md
in full, then this file, docs/research/LOCAL_MAINLINE.md and rollout/advisor/slack
stop flags. Reconcile current decision/reason with newer user directions BEFORE
acting. Never clear a user stop; restart or flag inspection does not revoke it.
Explicit stop suspends work, consultation/publication and heartbeat, and cancels
Dot monitoring. Resume requires explicit user direction. Keep existing evidence.

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

Before60 minutes no normal/no-next-action finish. Early reasons: explicit stop,
actual tool/quota/runtime limit, genuinely necessary user decision, or supported
completion of the whole scientific objective. A missing hypothesis is not a
user-decision blocker. After60 continue useful work toward90, then end safely.
No idle padding, irrelevant proofs, old conclusions or infrastructure filler.
Before final RESEARCH reply use session finish with evidence; refusal means
continue, not bypass. no_viable_action after60 needs fresh substantive examination
of two alternatives. Refill executable memo; record actual time and ending cause.
Validator checks structure/time, not scientific truth or guaranteed App uptime.
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
LESS THAN TWO HOURS needs no prior Dot assessment. If expected duration is
TWO HOURS OR MORE (>=120 minutes, including exactly120), submit it to Dot for
necessity assessment BEFORE starting, with question/cost/cheaper alternatives.
Pending that assessment, do shorter independent work; do not split to evade it.
The user changed this threshold on2026-10-15 at20:31 JST through Dot, then
directly confirmed that change in this chat. This supersedes the old >1hour
threshold and the mistaken decision to retain it as a stricter local instruction.
A relayed user decision is distinct from ordinary CHAT_Comments advice; current
direct confirmation resolves this case. This is separate from Agent segment
duration and grants no uncontrolled jobs; safety and frozen caps still apply.

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
For static values preserve equivalent-rule consistency, finite-board saturation
and supported scope; distinguish raw/normalized/rounded/clipped results. Quantity/
actor-splitting are empirical, not assumed linear conservation. Fix attack/search
conditions; distinguish ordering prices from leaf prices.

## Slack and delivery

Sole channel: NanoMelon #generic-chess C0C6L21UU20. Connected-account sends and
reasoned recontact are continuously authorized until revoked; stop suspends them.
Dot is a near-peer research partner, not permission issuer or publication gate.
CHAT_Comments are reference suggestions, not mandatory instructions/new authority.
Adopt/defer/reject using current user directions and evidence.

Read new channel roots AND relevant full threads/pages at recovery/useful
checkpoints, including completed-request supplements. Save exact output before
reconcile. Use existing consult/consult-status/reconcile and immutable IDs/hashes/
root ts. Delivery is not reading, response, adoption or independent execution.
User-directed inquiries to Slack ALWAYS get a fresh AGENT_REQUEST/new REQUEST_ID/
new thread. Agent-initiated technical followups may use the original thread plus
unique FOLLOWUP_ID. Never rebind advisor supplements as original roots.
Reconcile uncertain sends before deliberate retry; record purpose/evidence/
duplicate risk, no automatic retry/self-reply loops or ledger reset. Details:
docs/operations/SLACK_WORKFLOW.md. No per-attempt renewed consent.

Daily10:00 Asia/Tokyo is the main substantive consultation window; skip empty/
duplicate questions and missed-day catchup. Otherwise work independently. One
native90-minute same-chat heartbeat, no overlapping writer. No Goal, Windows
scheduler, Courier, native Chat sending, Supervisor or Socket Mode prerequisite;
no Dot/transport workers. Preserve configured notification intent; notify useful
results, failures or required decisions, not unchanged routine checks.

Git is version control/final delivery. Each completed segment commit/sync reviewed
project work to origin/sandbox using generic-chess-local.cmd publish --tests
<relevant pytest targets>; inspect outgoing diffs/history/archives, run checks and
verify FULL remote SHA. Do not claim a local commit was published or force-push.
Master promotion only tested fast-forward. User stop suspends publication; old
held-publication notes are historical, not current approval gates. Public read
access does not prove delivery or Dot reading every file. Existing repository
layers/recovery: docs/operations/REPOSITORY_LAYOUT.md and REBUILD_20261003.md.
Default pytest covers four active layers; retired receipts remain history.
