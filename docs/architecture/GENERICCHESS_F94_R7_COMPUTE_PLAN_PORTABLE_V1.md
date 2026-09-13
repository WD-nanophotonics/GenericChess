# F94 R7 portable compute-plan and resource-envelope specification

This tracked specification is the portable scientific description of the R7
plan. It is separate from the ignored runtime plan's current-SHA binding, so
adding this document cannot create a self-referential commit-hash loop.

## Scientific decision and fixed sample

The prospective decision is whether the frozen Layer-D endpoint rule can be
evaluated on fresh, identity-bound R7 evidence. The fixed sample is two
controls × three fresh tapes × three matchups × six role-swapped pairs × two
games: 18 invocations, 108 pairs, 216 games, and 216 action traces. The primary
endpoint is `4096_vs_256`; `1024_vs_256` and `4096_vs_1024` are diagnostics.
Seeds `9811/9812/9813` are fresh and disjoint from R6 `9801/9802/9803`.

A smaller run is insufficient because it would omit a preregistered control,
tape, diagnostic, or complete pair. That omission creates selection bias and
cannot establish the endpoint's strict positive-direction and pair-bootstrap
confidence gates. Partial or early-stopped evidence therefore remains
non-authoritative.

## Portable envelope

The review envelope is: 20 logical CPUs; four bounded concurrent lanes; 35
expected and 120 hard wall minutes; 12 expected and 24 hard CPU-hours;
8/16 GiB expected/hard peak RAM; 800,000,000 maximum nodes; 163,296 maximum
plies; 216 maximum games; one stage; no nested native engine threads. Pair-level
checkpointing is resumable and all raw runtime evidence remains outside Git.

## Exact runtime binding (reported after final source SHA)

The runtime artifacts are:

- `.generic_chess_flow/compute-plans/f94-r7-layer-d-authority-20260913-v1.json`
- `.generic_chess_flow/compute-plans/f94-r7-layer-d-authority-20260913-envelope-v1.json`

Their plan SHA, envelope digest, and bound source SHA are supplied in the
same-REQUEST Courier followup after this portable document is published and
the runtime files are rebound to the final published source. Chat and the
registered Supervisor must approve those exact values independently before any
Heavy invocation.

## Authority and intervention boundary

This checkpoint authorizes only plan review; it authorizes no compute or
promotion. Routine same-request Courier recovery remains within the existing
bounded transport ladder. Any request for user intervention must record
evidence for: why intervention is indispensable; why existing authorization or
Agent capability cannot resolve it; and whether the request contradicts the
automated chain. Unsupported answers require mechanical recovery or a safer
path, not a user escalation.
