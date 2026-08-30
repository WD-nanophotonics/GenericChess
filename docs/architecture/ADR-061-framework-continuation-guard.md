# ADR-061: Framework continuation guard

- Status: Accepted
- Date: 2026-08-30

## Decision

Treat a Courier response with `GENERICCHESS_STATUS=CONTINUE` or a
`WORK_ORDER_ID` as an active lifecycle state. Persist that state independently
of the request directory and reject terminal `finish` until the work order is
completed or a genuine terminal status is received.

The agent policy and workflow documentation define the same invariant for
conversation behavior: checkpoints and closeouts are intermediate events;
only `COMPLETE`, genuine `BLOCKED`, an explicit user stop, or a hard user-facing
error can stop the task. The flow script validates all control fields and
preserves Local-mode isolation.

## Consequences

- An assistant cannot accidentally turn a `CONTINUE` closeout into a final
  answer through the repository flow.
- Invalid or incomplete Chat control footers fail closed.
- F23Q's reserved ADR-060 remains available for its reference-corpus work.
