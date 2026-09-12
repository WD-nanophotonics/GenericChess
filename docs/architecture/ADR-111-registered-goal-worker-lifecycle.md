# ADR-111: Registered Goal Worker lifecycle and bounded escalation

## Status

Accepted; supersedes ADR-110's “No durable Goal” decision.

## Decision

Only a registered low-level Worker may enable one persistent Goal. The Goal
means continuous execution of the same ChatCourier worker/session/request:
obtain an order, implement it, test, commit, publish, close out, and obtain the
next order. It ends only at whole-project terminal status, explicit user stop,
or a lawful Supervisor escalation. The Supervisor and all other tasks may
audit, message, HOLD, or resolve escalation, but may not create a Goal.

Every new round and context compression rereads `AGENTS.md` and `WORKFLOW.md`.
Normal Goal operation is checked by the existing hourly Supervisor audit;
message Watchdogs, daemons, a new Goal state machine, and new CLI are not
introduced. ADR-110's hourly audit, one-writer rule, and urgent HOLD remain.

## Escalation boundary

Immediate escalation covers HOLD; ownership or second-writer conflict;
framework `HUMAN_REQUIRED`; uncertain irreversible external effects;
permission or large-compute approval boundaries; and severe harness failure
where continuing can damage state. Ordinary technical problems require two
different reasonable attempts with no substantive progress, no remaining safe
local option, and a conclusion that another attempt only repeats the same
work. Root cause plus failing phase define “same problem”; new evidence, state
progress, or a new recovery phase resets the count. A valid upgrade sends one
structured report to the registered Supervisor and pauses.

Courier busy/rate limits with recovery progress, waiting on the same request,
diagnosable test/compile errors, incremental progress, Worker-owned lost data,
one checkpoint, closeout, phase COMPLETE, context compression, or temporary
absence of a work order are neither stop nor escalation conditions.

## Consequences

The existing Courier recovery, Supervisor HOLD, task messaging, and one-writer
controls remain authoritative. The Goal is durable intent only; it does not
authorize promotion, compute, external side effects, or bypass any gate.
