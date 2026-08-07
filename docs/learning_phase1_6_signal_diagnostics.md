# Learning Phase 1.6: TD Signal / Representation / Search Sensitivity Audit

## Learning path audit (real data flow)

`RuleSet → build_ruleset_profile → LearnableMaterialCheckpoint (Gen0 copies
profile) → TDLeaf trajectories (frozen evaluator, owner-0 perspective) →
self-play (Gen-N vs Gen-N, 10% random exploration) → checkpoint Gen N+1 →
paired fresh-engine arena → native AlphaBeta search`.

Key semantics confirmed in code: TD target `u_t = tanh(θ·x_t / value_scale)`,
leaf from the replayed PV, eligibility `e_t = λe_{t-1} + ((1-u_t²)/S)x_t`,
`δ_t = u_{t+1} − u_t` (`δ_T = z − u_T`), batch episode-after-the-fact update,
perspective fixed at owner 0, board/current + hand/base feature channels,
no bias term, deterministic canonical tie-break in the native search.

## Learner freeze audit

`git diff ba78728 -- tdleaf.py features.py selfplay.py` → **empty** (byte
identical). No learner or optimizer changes this phase.

## Diagnostic holdout corpus

`LearningDiagnosticCorpus`: 512 reachable, non-terminal positions generated
from the R2 16-opening corpus (seed 314159) extended by deterministic random
legal rollouts (corpus seed 42, plies 2–40); checkpoint-independent,
serializable, replay-validated. 485 unique position keys. Corpus id:
`c8b4d0b5…` (see artifact). Phase mix: opening/early/mid/late present
(R2 games are short and first-player-decided, so "late" positions are
relatively shallow).

## TD signal (Diagnostic A)

| seed | n | mean δ | mean |δ| | std | pos/zero/neg | mean trace norm | mean update L2 |
| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| 7 | 239 | −0.003 | 0.254 | 0.36 | 0.39/0.24/0.37 | 0.0013 | 0.0036 |
| 8 | 228 | +0.005 | 0.234 | 0.35 | 0.38/0.26/0.36 | 0.0017 | 0.0040 |
| 9 | 138 | −0.049 | 0.295 | 0.37 | 0.35/0.29/0.36 | 0.0011 | 0.0033 |

TD errors are non-zero, roughly balanced in sign, and not degenerate; they do
not vanish toward zero across generations (per-generation means stable). All
self-play games end in checkmate (R2 color dominance), so per-outcome
grouping is single-valued.

## Material feature bottleneck (Diagnostic B)

512 positions → unique feature ratio 0.861, 40 collision groups (max size 8,
median 2), 21.7% of positions in collision groups, zero vectors 0.6%. The
representation is **not severely aliased**, though 22% collision is
non-trivial.

## Evaluator change (Diagnostic C)

Gen0→Gen3 weight L2 delta 69–119; mean |ΔV| on the corpus grows per
generation (seed 7: 43 → 126; seed 8: 60 → 138; seed 9: 24 → 74), with sign
flips ~0.2%. The evaluator genuinely changes.

## Search decision sensitivity (Diagnostic D)

Fresh-engine searches at 4000 nodes on 512 positions:

| seed | Gen1 flip | Gen2 flip | Gen3 flip | mean |Δscore| Gen1/3 |
| --- | ---: | ---: | ---: | ---: |
| 7 | 0.39% | 0.39% | 0.59% | 44 / 122 |
| 8 | 0.39% | 0.39% | 2.93% | 60 / 137 |
| 9 | 0.20% | 0.20% | 0.59% | 24 / 75 |

Best-move flips are 0.2–2.9% even though evaluator outputs change by tens to
hundreds of material points — the AlphaBeta decisions on R2 are dominated by
tactics and are almost insensitive to the learned material weights.

## Deeper-search teacher (Diagnostic E)

Teacher = Gen0 evaluator at 20k nodes (self-agreement 0.875 vs 40k),
student = gen-g at 4k nodes, 64 positions. Best-move agreement is 0.72 for
Gen0 and unchanged (0.70–0.72) for Gen1–3: the learner neither improves nor
degrades alignment with a stronger search.

## Arena sensitivity (Diagnostic F)

Gen0 vs Gen0 with different node budgets (paired, fresh engines):

| budget pair | weak-side mean pair score | CI |
| --- | ---: | --- |
| 4000 vs 2000 | 0.406 | [0.31, 0.50] |
| 4000 vs 1000 | 0.266 | [0.14, 0.38] |
| 4000 vs 500 | 0.125 | [0.03, 0.25] |

The R2 arena **can** detect 8×–16× search-strength differences, so the
null learning result is not explained by an insensitive arena.

## Layered verdicts

* TD_SIGNAL: **PRESENT**
* REPRESENTATION: **SUFFICIENT_FOR_MEASURED_SIGNAL** (86% unique features)
* SEARCH_EFFECT: **DECISIONS_CHANGED** (but only 0.2–2.9% of positions)
* TEACHER_ALIGNMENT: **UNCHANGED**
* ARENA_SENSITIVITY: **ADEQUATE**
* NEXT_PHASE_DECISION: **INCONCLUSIVE**

## Observed / Inferred / Not established

**Observed** (measured facts): TD deltas non-zero and balanced; evaluator
outputs change substantially per generation; best-move flip rate 0.2–2.9%;
teacher agreement flat at 0.72; the arena detects 8× budget differences.

**Inferred**: the learning signal exists at the TD level and changes the
evaluator, but it almost never changes a search decision on R2 — the
evaluator→decision link is the weakest point, consistent with R2's
tactical, first-player-dominant games masking small material effects.

**Not established**: that material-only representation is the bottleneck
(features are diverse), that the learner is broken (updates are stable), or
that the arena is insensitive (it detects 8× budget gaps). Which fix
(PST, different ruleset, lower budgets, or signal revision) is correct
cannot be decided from this experiment alone.

## CLI reproduction

The full diagnostic stack is runnable end-to-end from the module entry
point (no learner code is touched by the CLI either):

```powershell
python -m generic_chess.learning.diagnostics --ruleset R2_weird_generic --seed 7
```

Full defaults: 512 corpus positions, 4000 student nodes, 40,000 teacher
nodes, artifacts under `artifacts/learning_phase1_6/<ruleset>/seed<N>/`.
Pass `--corpus-seed`, `--corpus-count`, `--student-nodes`, `--teacher-nodes`
and `--experiment-dir` to override; Phase 1.5 checkpoints are reused when
found, otherwise a fixed calibration protocol retrains Gen0–Gen3.

`--smoke` shrinks the profile (48 positions, 500 student nodes, 1500
teacher nodes, artifacts under `artifacts/learning_phase1_6_smoke/`) so the
whole pipeline can be verified quickly:

```powershell
python -m generic_chess.learning.diagnostics --smoke --ruleset R2_weird_generic --seed 7
```

Explicit `--corpus-count` / `--student-nodes` / `--teacher-nodes` /
`--artifacts` values still override the smoke defaults, so the smoke mode
is a profile preset rather than a separate code path.
