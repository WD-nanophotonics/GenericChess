# GenericChess Single-Run Execution Policy v2

This policy supersedes `continuous-execution-v1` wherever the two differ.

## Hard rule

For an inbox TASK that defines a complete multi-step scope, Agent MUST execute the entire scope in one run and MUST NOT deliberately divide it into checkpoints, milestones, phase-return points, or audit pauses.

The only valid end states are:

- `COMPLETE`
- `HARD_BLOCKED`

## No checkpoint semantics

Do not create a conceptual `checkpoint` merely because:
- a subsystem is implemented;
- a build passes;
- tests pass;
- a phase ends;
- a useful SHA exists;
- the next section begins.

Do not return a progress response at such a point.

Do not say:
- “next I will...”
- “current task is not complete; next step is...”
- “I have pushed checkpoint X...”
and then terminate the run.

If the TASK contains 20 authorized steps, execute all 20 before returning, unless hard-blocked.

## Git behavior

Commits and pushes are allowed purely as mechanical persistence / backup while the run continues.

They have no workflow meaning.

A commit or push MUST NOT:
- cause a pause;
- cause a progress report;
- cause Agent to wait for Chat;
- create an artificial phase boundary.

Normal behavior:

```text
edit → test → commit/push if useful → keep editing immediately
```

not:

```text
edit → test → checkpoint → report → stop
```

There is no requirement to manufacture intermediate SHAs. If a single final commit/push is practical, that is acceptable. If several commits are useful for engineering safety, make them silently and continue.

## Audit behavior

Chat audit is asynchronous and non-blocking.

Do not stop to request or await an audit.

If a new AUDIT artifact happens to arrive while the active TASK is still running:
- PASS: incorporate the information and continue.
- FAIL: fix it in current HEAD, add regression coverage, continue.
- No audit yet: continue.

The active TASK itself is the execution authority.

## Current task

For `native-semantic-runtime-search-002`, continue without another intermediate return through all authorized work:

- GCSemanticPosition
- strict pack/snapshot
- canonical semantic position key
- SHA-256 parity
- history/repetition
- exact legal actions
- S0–S4 executor
- attack/check layering
- effects/triggers/promotion/drop
- checked make
- trusted make/unmake
- recursive semantic perft
- Python↔Native differential
- randomized multi-ply parity
- runtime closure
- fixed-depth semantic AlphaBeta
- generic evaluation
- exact best action/PV
- Python minimax differential
- requested tests
- final push/report

Do not return to the user between these items.

## Hard blocker definition

Ordinary engineering failures are NOT hard blockers:
- compile errors
- test failures
- crashes that can be debugged
- differential mismatches
- refactoring needs
- design choices resolvable from repository authority
- large remaining workload

A hard blocker means further work genuinely cannot continue after reasonable recovery attempts, such as a required human credential/permission with no fallback, destructive repository inconsistency, or an unresolved product decision outside the TASK's granted discretion.

## Response invariant

Before ending a run, check:

```text
Is the active TASK fully COMPLETE?
or
Is further progress genuinely HARD_BLOCKED?
```

If neither is true, do not return. Continue executing.

## Persistence

Update `coordination/AGENT_EXECUTION_POLICY.md` to reflect this v2 policy and remove language that encourages conceptual checkpoints for one-shot TASK execution.
