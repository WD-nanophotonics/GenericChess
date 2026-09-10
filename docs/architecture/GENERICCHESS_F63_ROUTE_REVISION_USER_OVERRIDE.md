# F63 route revision — user-directed continuation

This report records the user's explicit decision to stop waiting for the old
R10 Heavy continuation and proceed with the revised scientific route. Existing
atomic evidence remains available under the ignored runtime evidence tree; no
checkpoint files were deleted.

## Runtime disposition

- Sandbox checkpoint before this report: `0130e3620f37bf73a6d77fde689c5a9aa3e7d29e`.
- The calibrated-venv R10 continuation used the exact approved plan
  `c312aec2370e6e6acd2869c471608b6ef253e825f49b6fc72b6c3eb8804f30a0` and
  envelope `37cd153ac74cdecafb5ced5a4eb6d14a6d26fa42ae04cce333c2bda0e21e1c5f`.
- Preserved progress: candidate-59011 common-4 calibrated `8/8`;
  candidate-59012 common-4 calibrated `6/8`.
- The user redirected and cooperatively paused the old Heavy after the already
  persisted evidence. Candidate-59013 was never launched.

## Revised funnel requested for the next Chat work order

1. Short tactical/search behavior.
2. Short-horizon middlegame/endgame tests.
3. A small number of complete Arena pairs.
4. Large final-candidate confirmation only after the cheaper gates pass.

Teacher agreement remains diagnostic and is not a hard promotion gate. External
engines are restricted to Arena opponents and benchmark use.

## Acceptance criteria to co-design with Chat

- Reuse the existing 24 correctness guards, D0/D1/D2 search-integration probes
  (16 each), action-spectrum holdout, exact solver, game-atomic checkpoint, and
  decision-bound infrastructure.
- Exercise four independent mid/endgame states with role swaps and a 64-ply
  short-range Arena. A truncation is `UNRESOLVED`, never a draw.
- Retain survivors through complete Arena stages of 2, then at most 4, then 8
  pairs; equal-budget paired strength is authoritative.
- Keep legal-action, state-transition, perspective/sign, terminal semantics,
  Native/Python parity, reproducibility, and atomic-recovery checks fail-closed.
- Any large computation requires a versioned resource envelope and compute plan
  with Chat and registered-Supervisor approval bound to the exact plan SHA,
  sandbox SHA, and envelope digest.

This is a route proposal and closeout coordination artifact, not authorization
to start a new Heavy or to implement the funnel before Chat returns the revised
work order.

## R2 execution result

Chat subsequently authorized `GENERICCHESS-F63-R2-STRENGTH-FIRST-CHEAP-FUNNEL`.
The minimal Stage 0 screen was implemented in
`scripts/f63_r2_strength_first_cheap_funnel.py` with a new output namespace;
there is no aggregate stage runner. To avoid over-engineering, the first
execution was reduced to three deterministic correctness-smoke roots (one
under each named D0/D1/D2 label), cached Gen1/exact probes, one deployment
search per candidate, and a single repeatability sample. It completed in about
102 seconds with no correctness hard failures for seeds 59011, 59012, or
59013. These smoke observations are diagnostic and do not eliminate a
candidate.

The work also appended the route update to the theory roadmap and persisted
the user's reusable anti-overengineering rule in `AGENTS.md`: one-off
engineering/process/safety scaffolding expected to exceed 30 minutes must be
stopped or reduced unless recurrence, avoided loss, maintenance cost, and the
failure of a smaller solution are justified in writing.
