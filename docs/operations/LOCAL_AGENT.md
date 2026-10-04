# Local Agent operations

AGENTS.md is the sole active policy. At every work start, restart, heartbeat
continuation and after context compaction, read .local_agent/NEXT_WORK.md first
and in full, before research, edits or consultation. Identify the previous
unfinished work, latest state and next direction; then read AGENTS.md and the
scientific mainline, check stop flags and verify the memo against the checkout.
Slack/dot is the only consultation
transport; docs/operations/SLACK_WORKFLOW.md is the communication manual.

NEXT_WORK.md is resume memory, limited to 20 lines and 2 KiB UTF-8. Retain only
recent status, research-segment start time, unfinished work, the next direction
and essential evidence links.
After a small milestone, rewrite it when that will help the next restart or
compaction; no rewrite is required for every probe. Overwrite/delete obsolete
and completed entries, never accumulate a diary or archive each memo revision.
Keep detailed results and historical evidence in research documents/Git, not
in the memo. If the memo is absent or stale, reconstruct a small current memo
from those sources before proceeding; never infer permission to clear a stop.

Carryover work is a starting point, not a single-order queue or a session scope
limit. Choose the next useful step independently without waiting for new orders.
A single experiment's resource/abort ceiling only limits that computation;
it never means the research session should end.

## Active continuation

### Research segment loop without Goal

At a normal manual research start or heartbeat wake, read memo/mainline and
stop flags first. Record an ISO UTC start time and mark the segment active in
memo. Select the current question and two evidence-sensitive follow-up routes;
these are provisional directions, not a compulsory queue. Reuse the active
segment's start time after compaction or an interrupted-turn recovery. After a
recorded normal ending, the next research wake starts a new segment. If start
time is unavailable, record recovery time and unknown earlier duration.

At each milestone, validate, assess the mainline consequence, then select and
begin the next useful step. Carryover completion, tests, documentation, memo,
commit and publication are checkpoints rather than final-response triggers.
Aim for 60-90 minutes of useful research: before 60 minutes continue if a useful
executable next step exists; after 60 minutes an effective line may continue
toward about 90 minutes, finishing at a safe checkpoint. Do not start a large
new computation solely to fill the remaining window. The target cannot ensure
App uptime and does not override stop instructions or any experiment cost cap.

Early ending requires user stop, a necessary user decision, actual quota/tool/
runtime limits, evidence-supported scientific completion, or no worthwhile
executable direction. For the last reason inspect mainline/recent evidence and
at least two alternatives; write why neither currently advances the research.
No extra probe is required just to document that decision. Negative results,
dot silence and successful publication alone never justify ending. No padding
with idle waits, repeated failed probes, irrelevant proofs or larger budgets.

At a normal ending overwrite memo with recent concrete progress, start time,
elapsed minutes, ended status/reason and next direction. Keep <=20 lines and
<=2 KiB UTF-8; remove superseded entries. Detailed phase evidence belongs in
the relevant research document. Abrupt endings remain unobserved; recover from
the persisted active memo rather than claim the time/stop reason was measured.
Bounded user requests to configure, explain or review are not research-duration
samples; complete their requested scope without inventing research to fill time.

### Duration-policy acceptance

Configuration rollout on 2026-10-04: runtime acceptance PENDING (0/3 normal
research segments observed under the new policy). During the next three normal
segments record start/end, elapsed minutes, linked phase evidence and any early
ending reason in this section. A phase-to-next-phase transition must show actual
work, not just a memo promise. Do not count waiting as effective research or
fabricate three sessions in this configuration turn. If the Agent again ends
near ten minutes without a qualifying reason, inspect that turn and revise the
specific instruction; do not call persistence fixed from static checks alone.
No extra scheduler, worker, model setting, Goal or CLI interface is introduced.

Observation 1 is ACTIVE, started 2026-10-04T06:45:35Z (normal user continuation).
Actual phase continuation: public board-action goal intervals were implemented
and tested, then source inspection exposed missing Session declarations and
the adapter was extended/tested without ending the turn. Evidence:
docs/research/PUBLIC_GOAL_INTERVAL_RESULTS.md. A third phase read/reconciled
dot's concrete theory reply, corrected the overstrong calibration prerequisite,
then implemented/tested partial decision regret and paired optimum cancellation
(docs/research/PARTIAL_DECISION_LOSS_RESULTS.md). User's subsequent standing
Slack authorization was persisted without changing schedule or adding workers.
End/time/reason not yet observed;
this active segment is not a completed acceptance sample.

The first native same-chat heartbeat was received with event timestamp
2026-10-03T13:52:48.439Z. It resumed this checkout without another chat or Agent.
This observes receipt and local continuation; repeated two-hour cadence and
overlap/explicit-stop fault scenarios are not thereby proven. The receipt and
remaining limits are recorded in .local_agent/rollout.json.

The latest user instruction accepts active Slack plugin reading/waiting and
one native two-hour heartbeat on this same Agent chat. In this workflow,
the user's standing authorization permits in-scope sends to NanoMelon
#generic-chess C0C6L21UU20 and its threads through the connected account without
per-send confirmation, until revoked; explicit project stop suspends sending.
This persists across turns/restarts/compaction. See SLACK_WORKFLOW.md for scope
and the unchanged identity, deduplication and no-loop procedure.
During active work, check pending threads at relevant checkpoints; when awaiting
a useful answer, briefly wait and read again. Preserve useful partial evidence; do not stop at
an empty read, finished consultation, test or commit. Continue independent
bounded research during delays. No receive-only app or native reply wake is
required. Dot's Slack event subscription is already observed working.

The daily 10:00 Asia/Tokyo inspection is the main advisor window: ask about
major problems or substantive new theory, without duplicate/empty requests or
missed-day catchup. Two-hour inspections are local recovery, not mandatory
consultation. Ordinary project work proceeds independently; external discussion
is reserved for concrete issues. Receiving an opinion requires no reply or
acknowledgement. Record its assessment locally and ask follow-ups next time
unless the issue is time-sensitive. No response is a gate to independent work.

The native heartbeat checks user_paused/stopped before continuing, reconciles
pending consultation and resumes the scientific route. It targets the same
chat and never creates another task/Agent. A current active turn must not be
joined by a second writer. First scheduled wake timing is operational evidence
collected later, not a fabricated completed test. The old Windows task stays
absent/disabled; old Goals, queues and ownership rules are not restored.

For explicit stop: generic-chess-local.cmd stop persists user_paused/stopped
and disables consultation. The calling Agent also pauses native automation
and asks dot to cancel channel monitoring. Restart never clears stopped state.
Native continuation/local execution use the local Agent's allowance; dot must
not delegate additional Work/Codex execution. Aggregate account percentages
are not proof of a request's quota attribution.

## Version delivery

Inspect outgoing diffs, then publish --tests TARGETS. Verify full origin/sandbox
SHA. A tested published candidate can promote --candidate SHA --tests TARGETS
by fast-forward in this checkout. No Chat approval or sibling checkout.

## Recovery and historical evidence

REBUILD_20261003.md records earlier recovery stages; dated capability statuses
there are not current gates. Retired native/Courier/Socket prototypes and prior
policy bytes are indexed in docs/archive/workflow_retirement_20261003/INDEX.json.
Only resource-budget/path helpers were extracted from the old control program;
no scheduling, ownership or Supervisor code remains callable.

Verified archives are at E:\CodexArchive\20261003-rebuild and original retired
checkouts at C:\Users\wdai\CodexRetired\20261003-rebuild. CodexRecovery is unchanged.
Restore verified copies separately and repair Git pointers as documented. Never
import old App databases, credentials, Goals or queued work into the fresh App.
Sensitive App-state archives stay user-restricted and out of Git/attachments.
