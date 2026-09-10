# GenericChess F64 zero-compute generation-operator contrast

Work order: `GENERICCHESS-F64-ZERO-COMPUTE-GENERATION-OPERATOR-CONTRAST`

Parent repository SHA: `6d78a1d286c4230b8ff9aed4bcdbef453ba21773`

This is a diagnosis-only pass. It used the 96 already persisted F62 action
spectra, their cached action features and q20k teacher actions, and the frozen
Gen0/Gen1/Gen2 model parameters. It ran no Arena, self-play, teacher search,
action-spectrum generation, seed sweep, external engine, or Heavy job. The
machine-readable arithmetic is retained in the ignored runtime file
`.generic_chess_flow/f64-zero-compute-generation-operator-contrast/contrast.json`.

## Frozen identities and comparison definition

The common corpus contains 96 roots and the same legal action rows per root.
Gen0 is the parent checkpoint
`2c98cdd7c9e7b878decb15c2baf91b9d0150c65953e22481ce607d926ae43362` and has
no compact nonlinear residual. Gen1 is the accepted checkpoint
`d0e6a02482bb316e657ec6ef5c4f9379e6e7946d2da1a9a38647175567aecab4`.
The frozen replacement children are seeds 59011, 59012, and 59013; 59012 is
the persisted F62 child and the other two are reconstructed from the same
persisted F62 fit evidence. Seed 59013 remains unresolved in strength terms;
this report does not classify it as weak.

For every cached action row, total q was evaluated as `base_q + residual(features)`.
Gen0 therefore uses `base_q`; Gen1 and the children use their frozen compact
residuals. A policy decision means the highest total-q action with the cached
action-key tie break. The cached q20k spectrum top action is the teacher
reference.

## Discriminative results

* Gen0 and Gen1 choose different top actions on 46/96 roots. The replacement
  children retain Gen1's top action on 72/96 (59011), 72/96 (59012), and
  71/96 (59013); their top-action changes are therefore 24, 24, and 25.
* On the 24 roots whose Gen1 top-two margin is at or above the corpus upper
  quartile (`4,648.78`), the children change only 2, 3, and 3 decisions.
  Large-margin Gen1 choices are mostly retained, so the dominant issue is not
  indiscriminate top-action destruction.
* Every child reverses a Gen0-to-Gen1 top-action change on only 3 roots. This
  is a small direct reversal rate, but the three children make almost the same
  new replacements: their pairwise top agreement is 92.7%, 93.8%, and 99.0%,
  while their agreement with Gen1 is only 75.0%, 75.0%, and 74.0%.
* The same contrast appears in the full action order. Mean centered output
  correlation is 0.989–0.991 between children, versus 0.699–0.707 between a
  child and Gen1. Thus the failed/persisted children are much closer to one
  another than to the successful Gen1 policy surface.
* Residual scale expands sharply: Gen1's maximum absolute residual on this
  corpus is `20,303`; the children are `242,992`, `239,661`, and `239,574`.
  Their median top-two margins are about `32,877`, `31,368`, and `32,589`,
  versus `2,901` for Gen1. This is consistent with a fresh replacement model
  discarding the parent policy scale and over-correcting toward a common
  replacement operator.
* The child changes are not all unsupported: among changed roots, 10/24,
  10/24, and 10/25 land on the cached q20k teacher top action. The remainder
  are changes away from both the Gen1 decision and that cached teacher action.

Two informative roots are enough to show the split. At root 3, Gen1 selects
`P [3,3]->[3,4]`; all three children select the cached teacher
`N [1,0]->[0,2]`, while Gen0 selects `K [4,0]->[3,1]`. This is a justified
operator correction, not evidence that every child change is harmful. At root
20, Gen1 selects `K [5,8]->[4,8]`; 59011 and 59013 both replace it with
`G [3,8]->[4,7]`, while 59012 retains Gen1, and the cached teacher is
`B [2,6]->[4,4]`. This is a common child regression away from both references.
The previously selected root 84 remains stable: all four learned policies
select `P [6,2]->[6,3]`, with Gen1 margin `3,635.40` and child margins
`67,210.50`, `48,904.57`, and `61,708.63`.

## Exact trust-region algebra

For a child `C`, define the analysis-only interpolation

`Q_alpha(a) = Q_Gen1(a) + alpha * (Q_C(a) - Q_Gen1(a))`, `0 <= alpha <= 1`.

If `t` is Gen1's top action and `r` is a rival, their difference is affine:

`D_r(alpha) = D_r(0) + alpha * (D_r(1) - D_r(0))`.

When `D_r(0) > 0` and `D_r(1) < 0`, the exact first breakpoint is

`alpha_r = D_r(0) / (D_r(0) - D_r(1))`.

The first possible Gen1-top change is `min_r alpha_r`; no alpha grid was
evaluated. Across roots with a change, the minimum/median first breakpoints
are:

| child | roots with a breakpoint | minimum | median | high-confidence safe upper bound |
|---|---:|---:|---:|---:|
| 59011 | 24 | 0.001637 | 0.054858 | 0.155661 |
| 59012 | 24 | 0.001664 | 0.049053 | 0.192866 |
| 59013 | 25 | 0.001713 | 0.068372 | 0.184648 |

The last column is the smallest breakpoint among the 24 Gen1 high-confidence
roots when such a breakpoint exists; it describes a nontrivial interval that
preserves those high-confidence Gen1 decisions. The much smaller corpus-wide
minimum comes from low-margin roots, so an unconstrained full replacement has
no useful global safety interval. Within the changed roots, 10 per child
follow the cached teacher action, which identifies the only changes supported
by the preserved action evidence without pretending the teacher is a strength
authority.

## Diagnosis and one next mechanism

The replacement-forgetting hypothesis is supported on this frozen batch:
children are strongly similar to each other, strongly separated from Gen1,
show a roughly twelve-fold residual-scale expansion, and make a repeatable
set of common policy changes. It is not a claim that the learning mechanism
is globally impossible, and it does not classify unresolved seed 59013 as
weak. It does reject spending more strength compute on this same frozen
replacement batch as low-information.

The single selected mechanism is **`PARENT_RETENTION / BOUNDED_CORRECTION`**.
The minimal next learning modification is to retain Gen1 as the immutable
policy/value anchor and learn only an additive correction, with the correction
bounded or blended so that high-confidence Gen1 actions remain unchanged over
the analytically certified interval. The exact trust-region formula above is
the design constraint; this work order does not implement a learner, sweep
alpha, train a checkpoint, or authorize a strength run.

F63 is therefore closed as `F63_FROZEN_REPLACEMENT_BATCH_NOT_WORTH_FURTHER_STRENGTH_COMPUTE`.
Gen1 remains champion. The caveat is
`59013_UNRESOLVED_NOT_CLASSIFIED_WEAK`.
