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
Do not tune exposed/human labels, read the Xiangqi human holdout, exceed original
experiment caps, repeat failed batches or substitute framework work for science.

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

Next3 NORMAL segments after this rebuild are pending observation, not declared
passed. session_receipts.json retains at most3 summaries; session.json retains
the current/last segment. Inspect actual phase chains, elapsed time and evidence
for effective research. A short hard-blocked turn is recorded separately, not
a duration pass. A two-minute voluntary exit fails; diagnose the execution
break instead of relabelling it or writing retroactive justifications.
Pre-rebuild34-minute and80-second failures remain historical evidence in
docs/archive/continuation_before_20261004; they are not new-policy successes.

One native two-hour heartbeat, same chat, unchanged schedule/notification intent.
Daily10:00 Tokyo substantive dot window, no mandatory external response or
routine acknowledgement. Standing Slack authorization and complete-reply/
uncertain-send handling: SLACK_WORKFLOW.md. Explicit stop persists flags;
Agent pauses heartbeat/cancels dot monitoring, no scheduled automatic resume.
Transport/local Agent allowance boundaries remain in advisor.json.
Inspect outgoing diffs, run relevant tests, publish and verify origin/sandbox.
Recovery/isolation evidence remains REBUILD_20261003.md; never import old
App databases, credentials, Goals or retired queues. Do not touch other projects.
