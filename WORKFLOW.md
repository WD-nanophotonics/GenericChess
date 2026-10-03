# GenericChess workflow

One local Agent researches, implements, tests and delivers on sandbox. Dot
analyses and challenges evidence through #generic-chess. User instructions
prevail; neither partner is a publication gate.

Use generic-chess-local.cmd consult --question-file QUESTION.txt to prepare,
consult --begin-send REQUEST_ID before one Slack plugin send, then
slack-bind-sent --request-id REQUEST_ID --channel-id CHANNEL --message-ts 'ROOT_TS'.
Save the complete Slack read_thread tool result and run reconcile --request-id
REQUEST_ID --snapshot-file SNAPSHOT.json. Record adopt/defer/reject with reasons.
Read every reply/page, including later posts. Status summaries flag unreviewed
additions; --full returns the preserved full request/reply when needed.
See docs/operations/SLACK_WORKFLOW.md for the snapshot schema and uncertain-send
rules. consult-status reports persisted progress without spawning a model.

While active, read/wait/reconcile pending advice and continue useful independent
work. A pending reply or checkpoint is not a reason to end research. One native
two-hour heartbeat resumes this same chat if a turn unexpectedly ends. Consult
at the daily 10:00 Tokyo inspection for major problems or new theory; skip empty
or duplicate questions and do not catch up days. Two-hour inspections resume
local work without requiring dot. Midday work is independent by default; ask
only when a concrete issue merits discussion. Advice may be received without
replying; follow-ups can wait for the next consultation.
An explicit user stop suspends consultation and continuation persistently.
No extra receiving app or immediate model wake is required by this workflow.

Git is final delivery: publish --tests TARGETS pushes sandbox with tests and
full remote SHA verification. promote --candidate SHA --tests TARGETS performs
an ordinary tested master fast-forward. Never force-push. Retired control
code is preserved as text in docs/archive/workflow_retirement_20261003; it is
outside executable imports and command routes. Other projects are excluded.
