# GenericChess local research policy

This is the sole active policy. User instructions take precedence. One local
Agent works on sandbox in this checkout, in ordinary task mode. At every work
start, restart, heartbeat continuation and after context compaction, first read
.local_agent/NEXT_WORK.md in full. Understand the last unfinished work, current
state and next direction before acting. Then read this policy and
docs/research/LOCAL_MAINLINE.md and check persisted stop flags/current state.
Do not start extra Agents, concurrent heavy jobs or Work/Codex delegates.
Preserve research evidence, unrelated changes and Chess/Shogi/Xiangqi boundaries.
Choose the smallest decision-changing observation; bound compute and abort costs.
Local memo is compact resume memory: at most 20 lines and 2 KiB UTF-8. Keep only
recent state, research-segment start time, unfinished work, next direction and
necessary evidence references.
After a small milestone, optionally overwrite it; remove superseded/completed
items instead of appending history or retaining each memo version. Detailed
evidence belongs in research documents/Git. Memo is revisable planning memory,
not an approval queue or a limit on work. Select the next research question
independently. Experiment resource caps do not end the working session.

For each normal research start or heartbeat continuation, aim for 60-90 minutes
of useful research without Goal. Record the segment's UTC start time in memo;
choose the current question and two possible follow-up directions, revisable
by evidence. After each milestone: validate the result, assess its mainline
effect, then select AND BEGIN the next useful step. Documentation, memo updates,
tests, commits and publication are checkpoints, not reasons for a final reply.
Completing the carried-over memo items does not complete the research segment.
Before 60 minutes, continue whenever a useful executable next step exists.
After 60 minutes, continue an effective line toward roughly 90 minutes, then
finish at a safe checkpoint. This is a work target, not guaranteed App uptime.
Do not pad time with waiting, failed-probe repetitions, irrelevant small proofs
or enlarged compute budgets; each experiment retains its own abort/resource cap.
After compaction or recovery of an interrupted segment, read memo first and
preserve its start time. A normally ended segment's next wake starts a new one.
Early ending is allowed only for user stop, a decision requiring the user,
actual quota/tool/runtime limits, evidence-supported scientific completion,
or no worthwhile executable next step. Before the last conclusion, inspect
the mainline/recent evidence and at least two alternative directions; record
why they cannot currently advance it without running unnecessary experiments.
Dot silence, a negative result or publication alone never qualifies. At ending,
record concrete progress, elapsed time and reason; if abruptly interrupted,
mark the ending/time as unobserved rather than inventing a completed session.
Retain the compact memo limits; detailed evidence belongs in research documents.
This duration policy applies to normal research, not a separately requested
bounded configuration, explanation or review task.

The Agent and dot are research partners of nearly equal authority. Resolve
questions by evidence; record why advice is adopted, deferred or rejected. Dot
is not a work-order issuer or a publication gate. User instructions win.

Slack #generic-chess is the sole consultation channel. Use consult,
consult-status and reconcile with the calling Agent's installed Slack tools.
The user grants standing authorization for this GenericChess workflow to send
through the connected user account to NanoMelon #generic-chess C0C6L21UU20 and
its consultation threads. This is not per-turn permission: do not ask again
for in-scope sends. It lasts until user revocation; an explicit project stop
suspends sending. The user identifies this as their own dedicated workspace.
Authorization does not require routine sends or waive identity, deduplication,
uncertain-send reconciliation, no-loop or no-extra-worker rules.
Requests have immutable IDs, content hashes, project, channel and root ts.
Sender identity is the verified Slack account; role markers are not identity
proof. Dot currently replies using the same user account. Provide bounded code
or evidence with hashes; a local path does not grant dot filesystem access.
Git is version control and final delivery, not required communication.

During an active turn, read pending threads and, when useful, wait briefly then
read again without ending merely because a reply is pending. A bounded wait
expiry is a checkpoint: continue independent work or read again. Persist the
full tool response and reconcile before adopting advice or sending a new query.
Read all replies/pages; a completed request can still receive further posts.
Review flagged new evidence explicitly, without silently repeating old decisions.
Uncertain sends are never retried or switched to another channel. Edits and
additional replies are evidence, never automatic re-execution of decisions.
Daily inspection at 10:00 Asia/Tokyo is the main dot consultation window: check
for major problems or ask substantive new theoretical questions. Skip empty or
duplicate questions and never catch up missed days. Between daily inspections,
work independently by default; consult only a concrete issue needing discussion.
Receiving useful advice needs no acknowledgement or immediate reply. Reconcile
evidence when needed, record decisions locally, and raise follow-ups next time.

One native two-hour heartbeat continues this same chat as recovery from an
unexpected turn end. It must not create a second writer or overlap an active
turn. The latest user instruction accepts active plugin reads with this fallback;
two-hour inspections never require external discussion or an advisor response
before local work can continue. Read useful advice without adding reply loops.
Socket Mode, immediate model wake and a separate receiver app are not gates.
No Windows scheduler, old Goal, ownership capsule, Supervisor/Worker policy,
Chat approval or browser Courier is in the active call chain. Historical text
snapshots are evidence only and must never be executed or imported.
Ordinary dot consultation and transport must not launch extra workers. Local
Agent work and native continuation use the Agent's normal allowance. Quota
qualification is recorded in .local_agent/advisor.json; do not infer it from
unchanged account percentages or extend it to native Chat/Courier sends.

An explicit user stop suspends consultation and the heartbeat, and cancels dot
monitoring for this project. Persist stopped state; no scheduled turn may clear
it. A phase, consultation, test, commit or turn boundary does not establish the
scientific objective complete. Notify only meaningful results, failures or
required decisions. Continue independent research when dot is unavailable.

Before publication inspect the exact outgoing diff for sensitive/unrelated
content and run relevant tests. Publish to origin/sandbox and verify the full
remote SHA. Master promotion is a tested fast-forward of published sandbox in
this repository. Never force-push. Report local/published status accurately.
Never touch alphasho, its audits, tasks or other projects.

Operations: docs/operations/LOCAL_AGENT.md and docs/operations/SLACK_WORKFLOW.md.
Recovery evidence: docs/operations/REBUILD_20261003.md.
