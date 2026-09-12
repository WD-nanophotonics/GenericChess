# ADR-110: Hourly Supervisor audit and urgent HOLD

## Status

Superseded by ADR-111; hourly audit and urgent HOLD remain in force.

## Decision

GenericChess uses one persistent Luna High worker task and one persistent Sol
Medium Supervisor task. Chat remains the worker's direct project manager through
ChatCourier. The Supervisor is an hourly peer auditor: it inspects repository,
handoff, Courier, and worker-task state; wakes the same worker after an
unjustified stop; queues ordinary corrections; and does no routine product work.
The former “No durable Goal is required” decision is superseded by ADR-111;
only a registered low-level Worker may enable the Goal for the same
ChatCourier loop. The Supervisor and other tasks remain prohibited from Goals.

Urgent execution drift uses a Supervisor HOLD distinct from Courier transport
escalation. Only the registered Supervisor task may create or release it. The
ignored runtime record binds the HOLD to exact Supervisor and worker task IDs,
retains evidence, and stores a hashed release. Flow commands and Git hooks block
all durable worker progress while the HOLD is active. The worker carries the
evidence to ChatCourier for resolution; unresolved authority conflicts reach the
human user.

The ignored `supervisor-audit.json` record stores the latest classification,
worker status/cursor, message key, and HOLD ID. Message-bearing decisions reserve
a key before delivery; repeating the same key at the same worker cursor is
rejected, so an hourly wakeup does not repeatedly queue the same intervention.

## Consequences

An hourly audit can be cheap when work is healthy and can restart a worker that
ended without a legitimate stop. The existing event-driven Courier recovery
path remains unchanged. A HOLD cannot cancel an edit operation already executing,
but it prevents that work from being committed, pushed, closed out, or promoted.
There is still exactly one writer, one Chat target, and one immutable Courier
request at a time.
