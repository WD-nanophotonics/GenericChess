# Effective work accounting and durable hourly patrols

## Decision and cause

The wall-clock session gate previously accepted60 elapsed minutes plus one
research stage; a fresh stage after a long interruption could pass without60
minutes of research. The new timing unit is cumulative confirmed research work
within the same segment. This is a user-requested bounded configuration repair,
not a research-duration acceptance sample.

The existing DEV_AUX and PRIMARY hourly schedules retain their identities,
chat targets, recurrence, enabled state and notification settings. Their prompts
contain only role/root/branch binding and the durable recovery, useful-work,
duration, stop, communication/publication and handoff loop. Temporary scientific
choices, dates, old failures and duplicated communication rules stay in the
role's current local records. PRIMARY code/state is not changed by this patch.

## CLI and lifecycle

1. `session start` creates or resumes the owned segment; ID and UTC origin stay
   unchanged on resume. Legacy active sessions migrate without inferred credit.
2. `session work-start --question QUESTION` opens one actual research interval.
   A second open interval is rejected. Do not start one for administrative work.
3. `session work-stop --evidence REF` closes it at the current time. REF identifies
   the concrete command output, experiment receipt, implementation/test or
   analysis result. Research checkpoints record the question/result/next action.
4. Close work before standalone configuration, message transport, publication,
   idle waiting or ending a turn. Documentation/transport checkpoints reject an
   open research interval. Start the next interval only when useful research
   actually begins. Time spent testing/implementing a research question counts;
   merely sending, pushing or waiting does not.
5. Resume preserves all closed intervals. An open interval is archived as
   uncredited interruption evidence, not silently closed or counted. Repeated
   resume adds no credit. Concurrent computation and analysis count their union,
   not a sum; no new worker, service or scheduler is introduced.
6. `session status` exposes wall-clock `elapsed_minutes` separately from
   `effective_work_seconds`. Only closed evidence-bearing intervals contribute.
7. Normal `session finish` rejects an open interval, fewer than3600 confirmed
   seconds, missing fresh research or missing executable memo. A rejection means
   continue useful work, not send a final research reply. After60 effective
   minutes continue useful work toward90 and finish safely. Hard stop/limit
   reasons keep their existing evidence rules; unfinished work gets no credit.
8. Successful finish synchronizes the memo Segment with ENDED, ID, UTC origin,
   confirmed work time and reason. An explicit stop cannot be delayed by a
   missing or malformed memo; `memo_synced=false` records that case.

## Data and limits

New sessions use `work_accounting_version=1`, `work_intervals`, `active_work`,
`uncredited_work` when applicable, and derived `effective_work_seconds`.
Closed intervals contain question, start/end UTC and evidence reference.
Clock reversal, intervals outside the segment or beyond the current time, and
invalid timestamps fail closed. No arbitrary past start/stop timestamps are
accepted by the CLI. Existing finished records are not rewritten or relabeled;
legacy elapsed minutes never imply effective work. Keep exact original receipts.

This ledger verifies declared intervals and references, not cognitive activity
or scientific truth. A caller must close before idle/admin work and run start
on actual recovery; leaving a window open across undisclosed idle time cannot
be detected from timestamps alone. Independent command/run evidence remains
necessary. Local enforcement cannot prevent the app/model from exiting or
force a caller to invoke finish. Such an exit is an interruption or workflow
failure, never a compliant normal finish. Do not claim guaranteed app uptime.

## Verification and rollout

Regressions cover wall70/work5 rejection, the exact3600-second boundary,
disjoint accumulation across offline gaps, repeated resume, open-window
exclusion, double-open/close, required evidence, admin separation, overlap union,
invalid clocks, legacy migration and hard-stop behavior. CLI commands use the
same implementation as tests. Schedule readback must show the same ID, target,
hourly interval, enabled state and exact common role-bound prompt.

The next normal DEV_AUX research segment must use this ledger and publish its
real intervals, scientific checkpoints and finish receipt; fake-clock tests and
this configuration repair do not establish a live60-minute work sample.
PRIMARY may adopt the published helper in its own checkout under its ownership.


Delivery verification: all113 workflow tests passed. Both official automation
updates succeeded and were read back: dev-aux prompt2234 to669 characters;
genericchess828 to667. ID, target chat, hourly recurrence, ACTIVE status, name,
creation time and notification fields all matched the pre-update snapshots;
only prompt and update timestamp changed. The common prompt body is identical
across roles. Original configurations, exact tool receipts and readback hashes
are retained in DEV_AUX's ignored state. No PRIMARY files/state or paused
DEEPSEEK schedule were changed. These are configuration/guard checks, not a
completed normal research-duration acceptance sample.
