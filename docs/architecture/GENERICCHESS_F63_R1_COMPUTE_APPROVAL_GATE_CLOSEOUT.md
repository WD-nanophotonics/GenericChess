# GenericChess F63-R1 compute approval gate closeout

Status: compute-governance prerequisite implemented and published. No new
large computation was launched. The F63 scientific result remains the prior
user-override decision-only result: teacher-8 is 7/8 complete pairs, not a
completed 8-pair estimate.

## Published identity

- Parent work order: `GENERICCHESS-F63-R1-GAME-ATOMIC-ARENA-AND-CANDIDATE-RESUME`.
- Previous published checkpoint: `e34c2afe6b17a55de8b8255a303d8af0e6f18143`.
- Compute-gate implementation checkpoint: `39beee81dd5a46c41725bef82f522fcab40a7c8f`.
- `origin/sandbox` was synchronized to the compute-gate checkpoint.
- `master` remains `44fce4f9dfeee0ef9480597c7ab34195db984100` and was not changed.

## Enforced compute governance

Every `heavy` and `heavy-start` invocation now requires an explicit structured
resource envelope. The centralized policy is versioned at
`tools/compute_policy.json`. A run is conservatively large when any configured
threshold is met, or when an expected wall/CPU estimate is unknown.

Large work fails closed unless it supplies a versioned compute plan whose exact
current sandbox SHA, resource envelope, and command argv match the run. The
plan must state the scientific decision, why smaller evidence is insufficient,
reusable evidence, stages, checkpoint/recovery behavior, pause points,
early-stop rules, failure path, alternatives, and hard resource bounds.

The registered Supervisor-only commands are:

- `compute-plan-approve`
- `compute-plan-status`
- `compute-plan-revoke`

Approval records are runtime-only under `.generic_chess_flow/compute-approvals/`
and bind plan SHA, current sandbox SHA, canonical envelope digest, current
normal Chat response SHA, and registered Supervisor identity. Chat approval is
required through optional structured response fields; stale, forged, revoked,
wrong-Supervisor, changed-command, changed-budget, changed-stage, or changed-
SHA approvals fail closed. Approval is idempotent for the same exact plan and
cannot be reused for an altered plan.

The gate preserves the small/medium path, but even that path cannot omit a
resource declaration. It does not infer compute size from arbitrary command
text.

## Verification

- Compute-gate and flow tests: `61 passed`.
- Covered missing resource declarations, small-run pass-through, unknown
  estimates, large-plan requirement, valid Chat plus Supervisor approval,
  idempotent approval, forged/stale/wrong-Supervisor/expanded-plan rejection,
  revoke, and fail-closed Heavy entry points.
- No new Heavy is running. The stopped F63 run remains recorded as failed by
  the user-authorized termination and its raw evidence remains outside Git.

## Next explicitly bounded work

Before any expensive F63 resume, the next implementation must add per-game
atomic Arena checkpoints, game-level scheduling, exact-once deterministic pair
aggregation, pause and hard wall/node/game/lane caps, strict identity/replay/
role validation, and decision-aware stopping with separate
`decision_sufficient` and `strength_estimate_complete` metadata. It must add
crash/resume, out-of-order, partial-pair, pause, cap, concurrency, and result-
equivalence tests. Every future Heavy must carry a versioned compute plan,
Chat approval, registered-Supervisor approval, an upfront CPU/wall estimate,
and hard wall/node/game/concurrency ceilings before launch.

