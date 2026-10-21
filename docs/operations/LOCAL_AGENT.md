# DEV_AUX local operations

AGENTS.md is authoritative. This file contains current operating methods;
retired priorities, Dot windows and PRIMARY publication commands have been
removed. Their historical receipts remain in Git.

## Recovery

Read .local_agent/NEXT_WORK.md in full, then AGENTS.md, the current mainline
and own role/rollout/advisor/Slack stop flags. Use an explicit own-checkout
working directory; run `dev-aux-local.cmd doctor`. Identity must match DEV_AUX,
this repository root and sidemission. Never infer identity from app default cwd.
Check heartbeat binding or remote transport only when investigating that issue.
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

## Research and timing

Read LOCAL_MAINLINE.md for the current question. The direct2026-10-21 Leaper
redirection replaces expansion of the old TDLeaf panels. Use exact small-game
baselines, conditional value/policy comparisons and later learning diagnostics;
reuse the existing learner when relevant. Keep full executable rules/history
and UNKNOWN semantics.
Do not restore retired audit chains merely because an old memo names them.

Before substantive work, do one role-local mailbox probe per SLACK_WORKFLOW.md.
Review new/edited Chat comments with adopt/defer/reject reasons; advice does not
replace explicit user direction. The completed cleanup was read-only;
normal research follows the periodic mailbox protocol.
No Dot realtime wait, daily gate, resend or reply requirement.
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
>=120minutes first needs explicit Chat mailbox scope/budget assessment.
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
