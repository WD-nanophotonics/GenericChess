# Learning Phase 1: Learnable Material + TDLeaf(λ)

## Product goal

Prove that a fixed Alpha-Beta searcher in GenericChess can learn an
evaluation from its own self-play and produce a child checkpoint with
measurable, reproducible strength evidence against its parent — not high
Elo, but a working train→checkpoint→arena loop.

## Why Alpha-Beta stays

The native iterative Alpha-Beta engine (Phase 2C) is the fixed policy during
learning; only the material evaluation weights are learned. This isolates
the learning signal from search changes and keeps TT semantics valid within
a generation.

## Generation model

```
Generation N (frozen evaluator θ_N)
    → self-play Gen-N vs Gen-N (one frozen checkpoint)
    → TDLeaf trajectories
    → batch update θ_(N+1)
    → checkpoint Generation N+1
    → same-budget arena parent vs child (no exploration)
```
The evaluator never changes inside one game/search/arena match. Switching
generations always compiles fresh native evaluation tables and a fresh
`NativeSearchEngine` (TT never crosses evaluators).

## Learnable material

`V(s; θ) = Σ_t w_t (N^self_t − N^opp_t) + Σ_t h_t (H^self_t − H^opp_t)`
with `w` = board current-type weights and `h` = hand base-type weights, in a
fixed owner-0 perspective; anchors are excluded and never learnable.
Generation 0 copies the existing rule-derived `RuleSetEvaluationProfile`.
Float64 weights are quantized to native int tables with
`MATERIAL_SCALE = 1.0` (fixed and versioned in the checkpoint). After every
update the non-anchor board median is rescaled back to the frozen initial
median (target = `value_scale / 4`) and weights are clipped to `±w_max`.

## TDLeaf(λ)

For each self-play decision point `s_t`, the native search returns a PV;
the PV is replayed through Python Core to a leaf `L_t`. `x_t` = features of
`L_t` from owner 0, `v_t = θ·x_t`, `u_t = tanh(v_t / value_scale)`,
`value_scale = initial median material × 4`. TD errors:
`δ_t = u_{t+1} − u_t`, `δ_T = z − u_T` with `z ∈ {+1, 0, −1}` (owner-0
win/draw/loss). Eligibility `e_t = λ e_{t−1} + ((1−u_t²)/S) x_t`; batch
update `θ ← θ + α Σ δ_t e_t` computed episode-after-the-fact from the frozen
`θ_N`. Defaults: `γ = 1.0`, `λ = 0.7`, `α = 0.01 × initial weight scale`.

## Checkpoints

`LearnableMaterialCheckpoint` is RuleSet-specific (fingerprint validated),
stores weights/scale/counters/parent id, and its id is the SHA-256 of the
canonical serialized learning state. Training continues through the parent
chain (Gen 3 → Gen 4) without restarting.

## Self-play

`SelfPlayConfig(games, nodes_per_move, max_depth, seed, epsilon)`; temperature
0 with a single exploration rule: 10% of moves pick a uniform random Python
legal action, otherwise the native best action. Every TDLeaf point comes from
a real native search (PV replayed and verified in Core); exploration affects
only the played action, never the learned leaf.

## Arena

`ArenaConfig(pairs, nodes_per_move, max_depth, tt_mb)`: paired matches with
swapped colors, identical search/TT budgets, no exploration, fresh engines
per checkpoint. Reports W/D/L, child score rate and a Wilson confidence
interval. Elo is descriptive only.

## Proof standard

Correctness gates (hand-computed TDLeaf math, disturbed-weight recovery,
serialization replay, determinism, owner symmetry, baseline equality) plus a
pre-registered short experiment on three fixed RuleSets with 3 training
seeds for the most promising one. Verdicts: PASS / PROMISING / INCONCLUSIVE /
FAIL; negative results are allowed and reported honestly.

## Experiment results

Pre-registered proof experiment (seed 7; `alpha_target_l2_fraction = 0.10`,
gradient-calibrated rate; 5 generations; 8 self-play games/generation at 2000
nodes/move; 10 arena pairs (20 games) per generation at 4000 nodes/move).
Artifacts: `artifacts/learning_phase1/` (gitignored).

| RuleSet | fingerprint | child score (best gen) | notes |
|---|---|---|---|
| R1 classic-like 4×4 | `9b1e5e1b…` | 0.45 | outcomes color-dominated; no improvement |
| R2 weird generic 4×4 | `2c56e08b…` | 0.55 / 0.60 / 0.70 (seeds 7/8/9) | first trained generation improves; later generations oscillate |
| R3 promo/drop hybrid 6×6 | (see summary.json) | 0.50 | deterministic play always draws; zero TD signal |

R2 seed repetition: seed 7 best 0.55, seed 8 best 0.60, seed 9 best 0.70 —
the direction is consistent across three training seeds for the first trained
generation, but continued training is unstable (seed 8 gen 3 collapses to
0.00), so the signal is small and sample-limited.

Verdict: **PROMISING** — the training pipeline is correct, parameters change
meaningfully from real TD errors, and R2 shows a reproducible positive
direction, but arena samples are small and continued-generation stability is
not yet established.

## Limitations

Material-only learnable representation; no PST, mobility, n-tuple, NNUE,
teacher distillation, population, or UI training screen; native qsearch and
the production dynamic evaluator remain parked.
