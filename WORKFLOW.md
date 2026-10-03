# GenericChess workflow

One local Agent researches, implements, tests, records evidence and continues.
The ordinary Chat advisor supplies evidence and directions; the Agent records
its evaluation and keeps working. User instructions take precedence.

`generic-chess-local.cmd consult --question-file <file> [--daily] [--code-file <file>]`
prepares an immutable advisory request. `consult --begin-send <request-id>`
records uncertainty before the Agent sends via the native app tool. Then use
`consult-status [--request-id <id>]` or `reconcile --request-id <id>
--snapshot-file <native-read-thread.json>` to collect a complete anchored reply.
`reconcile --request-id <id> --decision adopt|defer|reject --reason <text>`
records how the advice affected research. No command launches a second model.

Daily consultation is at 10:00 Asia/Tokyo, with additional distinct on-demand
questions. One native two-hour heartbeat continues this same chat only after
acceptance. Pending capability checks leave the relevant automation paused.

Git is the delivery endpoint. `publish --tests <targets>` validates and pushes
sandbox; `promote --candidate <full-sha> --tests <targets>` fast-forwards remote
master without a sibling checkout. Chat approval and a prior Git publication
are not requirements for consultation. The retired flow launcher returns an
error and never invokes its historical implementation.
