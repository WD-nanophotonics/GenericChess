# DEV_AUX local operations

AGENTS.md is authoritative. Use [current status](DEV_AUX_CURRENT_STATUS.md)
for cadence and task ownership. This file contains current operating methods;
retired priorities, Dot windows and PRIMARY publication commands have been
removed. Their historical receipts remain in Git.

## Recovery

Read .local_agent/NEXT_WORK.md in full, then AGENTS.md, the current mainline
and own role/rollout/advisor/Slack stop flags. Use an explicit own-checkout
working directory; run `dev-aux-local.cmd doctor`. Identity must match DEV_AUX,
this repository root and sidemission. Never infer identity from app default cwd.
Check heartbeat binding only when investigating that issue. Remote review checks
are routine at work opening under CHATGPT_REVIEW_WORKFLOW.md, not restricted
to transport incidents.
Unknown process visibility is not evidence that a process exited.

An active session is authoritative even if the memo is stale. Use
`dev-aux-local.cmd session start` to resume without resetting UUID/origin or
confirmed effective work. Resume preserves unconfirmed intervals as interruption
evidence without granting credit. An ended session starts a new research segment.
No second writer, Agent, worker, Goal or replacement timer.

At every recovery/heartbeat, check the latest committed sandbox infrastructure
and reuse it as the default rules/search/history/runtime baseline in sidemission.
Keep the independent learner/research changes, not a second infrastructure fork.
Import committed source/tests with their dependencies, record the source SHA,
and resolve compatibility locally. Uncommitted mainline work stays untouched.
Verify actual learner callers before claiming performance gains. Only this
checkout is writable; old experimental results and caps remain frozen.
Fetch the explicit tracking ref with
`git fetch origin refs/heads/sandbox:refs/remotes/origin/sandbox`; the own-branch
fetch configuration may otherwise update only FETCH_HEAD and leave a stale
origin/sandbox. Inspect the fixed fetched commit before importing its files.

## GitHub and Slack review intake

At every new round/manual start/heartbeat, read the remote ChatGPT Patrol review
files and new/edited Slack autonomous comments before selecting research. Follow
CHATGPT_REVIEW_WORKFLOW.md: discover actual remote path/ref, explicitly update
needed tracking refs, pin full SHA/path/blob, compare changed files, retain exact
originals and incomplete-coverage boundaries. No merge/import/execution is needed
to read advice. Apply latest user > autonomous GitHub/Slack ChatGPT > Dot > local;
record adoption and actual execution separately. Current cadence/task state
comes from the status reference above; review intake itself does not mutate
scheduler/session/research state.

## Research and timing

Read LOCAL_MAINLINE.md for the current user assignment. The initial audit is
complete: wait for user assignment, without resuming the deferred P0/P1 queue.
Earlier learner-cost, TD and screen-first
automatic queues are superseded by the2026-10-23/24 direction. Preserve their
evidence/caps without launching an unstarted price or feature-policy reserve.
Later learning/teachers/inverse and search-knowledge compression are conditional
future work. Keep full executable rules/history and UNKNOWN semantics.
Do not restore retired audit chains merely because an old memo names them.

Before substantive work, complete own GitHub/Slack intake per
CHATGPT_REVIEW_WORKFLOW.md and SLACK_WORKFLOW.md.
Review new/edited Chat comments with adopt/defer/reject reasons; advice does not
replace explicit user direction. The completed cleanup was read-only;
normal research follows current review intake and restored bounded Dot dialogue.
Newround AGENT_REQUEST and one +5minute reply check apply; no empty polling.
Raw originals use the committed `save_plugin_original` helper, active session
UUID and a fresh read UUID per logical capture; see SLACK_WORKFLOW.md. Identical
retries preserve bytes, while a different existing original cannot be replaced.
Quote Slack timestamps in PowerShell native-command arguments; unquoted decimal
tokens can be rounded before the CLI receives them and fail exact-revision review.

Open a research interval using:
`dev-aux-local.cmd session work-start --question "decision-changing question"`.
At a milestone, close it with:
`dev-aux-local.cmd session work-stop --evidence "concrete source/result paths"`.
Record question, observation, evidence and next action with `session checkpoint`;
then begin the next useful research step. Use `--help` for exact arguments.
Admin, Slack transport, publication, offline gaps and waiting earn no work credit.
Do not close a stale interval as if an interruption were continuous work.

Normal research segments need at least3600 confirmed seconds, proceeding toward
5400 where useful. Do not pad time. Before a final research reply call
`session finish` with actual evidence; a rejection requires continuing, not
bypassing the gate. Explicit bounded cleanup/configuration is administrative and
must not be relabeled a completed research segment. Preserve any unfinished
research session for later continuation.

Missing ideas or silent advice are soft blocks: diagnose, derive a falsifiable
hypothesis or switch to a useful backup. A serious unfixable blocker requires
concrete evidence and the user action needed, following AGENTS.md. One inspection
pause does not change recurrence; only explicit schedule instructions do.

## Experiment cost and records

A single expected run under120minutes may proceed within standing scope;
>=120minutes first needs the required explicit scope/budget assessment under
current user instructions. GitHub/Slack are review intake, not automatic approval.
Do not split a run to evade assessment, reset an old cap, or extend frozen tests
based on observed results. Preserve failed/partial/censored and missing records.

For new exploratory work keep revision, seed, configuration and a compact result
summary. Put generated traces/checkpoints under ignored artifacts/. Add only
validation that tests a real semantic or execution risk. Do not add per-check
receipt/crosswalk files, duplicate JSONs or auditor prerequisites as a substitute
for running a useful bounded experiment. Retained historical frozen inputs keep
their original contracts; cleanup does not rewrite past experimental authority.

## Memo and delivery

NEXT_WORK.md stays <=20lines/2048 UTF-8 bytes, with State, Segment, Main,
Backup1, Backup2 and Evidence. Tasks use question | first action | expected
result | done condition. Replace completed/stale tasks; no diary.

Inspect actual outgoing changes for personal information, passwords and
credentials. Keep sensitive originals ignored. Run relevant tests, commit only
reviewed project work, then `git push origin sidemission`; verify the full
`git ls-remote origin refs/heads/sidemission` SHA equals local HEAD.
Do not use inherited publish/promote (PRIMARY branches), force-push or bypass
hooks. Repository remains PUBLIC unless explicitly directed otherwise.
Before every authorized Slack message first push and verify SHA, including when
no new commit is needed. Save exact outgoing text and delivery evidence. Existing
SEND_UNCERTAIN messages are reconciled at a later probe, never automatically
resent. The bounded cleanup's read-only restriction does not disable normal
research communication or the existing recurrence.

Keep a concise collaboration summary at meaningful research completion.
REPOSITORY_LAYOUT.md and CLEANUP_20261021.md explain dependency-preserving
cleanup and recovery. Default pytest covers product/development/workflow/
specification. Historical receipt tests are not active research requirements.

## Committed mainline clarification reused — 2026-10-22

From sandbox55abf3de22f20ac03eb07b5260284466173a3264:an inactive feature does
not require its default coefficient to be zero. Inspect the actual consumer
and profile constructor;distinguish an explicit proved-zero override from
the default complete table. Finite default hand prices can remain while stock
is unreachable. Do not rewrite a product expectation merely to match a table.
DEV_AUX keeps its own scope/state;this adoption imports no PRIMARY task or
default change. The shared package and tests have no delta from291f2c3.


## Committed mainline clarification reused — 2026-10-24

From sandboxaaa325e4286197ee731c7e61df5106251661f687: controller identity is
the actual complete constructor/weights, not a seed label or inherited writer
name. Distinguish fixed leaf prices from ordering and active dynamic terms.
Identical deterministic no-update controls are redundant paid executions, not
independent outcomes; retain and disclose their originals. Do not turn legal
leaf crossings, selected PV signal or a bad-action threshold into a learning
gate. Root choices and terminal payoff need their own evidence. Exact executed
UTF8 capsules are read as bytes; presentation normalization gets a separate hash.

DEV_AUX actual episode labels bind before/after weights and its unchanged public
q0 learner adapter; foes are the declared Unit model or recorded legal Uniform
stream. Imported PRIMARY profile metadata does not replace this actual caller
contract. This adopts methodological clarification only, not PRIMARY task/state,
controller defaults or another role's publication/recurring configuration.

## Latest committed source reused — 2026-10-24 depth study

Source56560fb3e24102792f72a005c5c5bdb52526943f supplies13exact imported paths.
The actual controller/slot-label erratum and generated-versus-served profile
separation are retained rather than rewritten; only pinned historical faulty
source hashes receive that reader exception. The workflow atomic writer retries
only the same complete temporary for Windows5/32/33, bounded to3attempts,
preserving old stops on permanent failure. Role-local session regressions pass.

AUX's complete static graph reader now accepts an EXPLICIT source input group,
defaulting to the old contact contract, to verify an actually constructed quiet
odd component under its own full RuleSet. Matching piece counts never selects
a graph or silently rewrites a root fingerprint. Actual owner qualifications,
history admission, query/receipt/capsule bytes and finite-opponent payoff remain
separate. This imports no other role's state, task, schedule or default.
