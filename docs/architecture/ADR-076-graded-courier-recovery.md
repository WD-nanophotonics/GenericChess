# ADR-076: Graded Courier recovery and Supervisor takeover

## Status

Accepted.

## Decision

Courier transport failure is not a business-level `BLOCKED` decision. The
workflow uses four authority levels: bounded worker recovery, read-only reuse of
the existing Chat conversation, a registered Supervisor task, and finally the
human user.

Every recovery starts with a fingerprint-bound read-only probe. If the original
request exists, the worker waits or recovers it without sending again. If no
request or reply exists and the evidence is fresh, unchanged, owner-free, and
submission-free, ChatCourier may retry that immutable request once. Any conflict
or further failure creates an idempotent dossier and stops worker writes.

Supervisor identity is an explicit `CODEX_THREAD_ID`. A claim is exclusive and
a resolution is hashed, records the original worker identity, and returns work
to the same task and request. Only the Supervisor may review ChatCourier's
separate one-time resend facility. Neither recovery nor escalation can expand a
work order, change the Chat target, or authorize promotion.

## Consequences

Temporary browser and transport failures no longer force human intervention.
The retry budget and immutable evidence prevent accidental duplicate sends.
Runtime identities, dossiers, locks, and raw probes remain ignored; protocol,
tests, and this decision remain versioned.
