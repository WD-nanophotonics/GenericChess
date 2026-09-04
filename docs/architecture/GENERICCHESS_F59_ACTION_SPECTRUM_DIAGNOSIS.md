# F59 action-spectrum diagnosis

Status: diagnostic complete; deployment and promotion remain on HOLD.

F59 is a policy-facing follow-up to F58. It freezes the F58 corrective parent
`dddd397891203da446da50fc23399d4cf9badae4`, the corrected F58 encoding, the
fixed width-32 tanh residual architecture, and the current v4 Shogi
observational comparator. The theory and decision hierarchy used here are in
[`GENERICCHESS_THEORY_ROADMAP.md`](GENERICCHESS_THEORY_ROADMAP.md). The
reviewer/supervisor requirement to read that roadmap is also recorded in
`AGENTS.md`.

## Protocol

The evaluator was examined on three distributions:

* D0: random reachable states.
* D1: states from v2 self-play.
* D2: states on deeper v2 principal-variation corridors.

Shogi used 36 roots per distribution, with the frozen first 24 roots as
development and the final 12 roots as holdout. Teacher stability was measured
by the top action from equal-budget child searches at 10k versus 20k nodes;
root-level stability was also measured at 40k versus 80k. Candidate-spectrum
regret is relative to the retained candidate set (cheap top six actions plus
the v2/v4 and teacher probe actions), not every legal action. Unstable teacher
roots were excluded from objective gates. D0, D1, and D2 were generated with
fixed seeds and fingerprints by `scripts/f59_action_spectrum_diagnosis.py`.

The Western run was a 12-root, diagnostic-only sanity run. It intentionally
did not train objectives or claim cross-game generality.

## Results

### Shogi action surface and baseline policy risk

| Distribution | Stable roots | Candidate actions (mean) | Legal actions (mean) | 10k→20k top action | 40k→80k root action | v2 2k→80k action |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| D0 random | 35/36 (97.2%) | 6.56 | 32.03 | 97.2% | 88.9% | 66.7% |
| D1 self-play | 36/36 (100%) | 7.25 | 36.64 | 100% | 77.8% | 52.8% |
| D2 PV corridor | 36/36 (100%) | 6.83 | 36.17 | 100% | 83.3% | 66.7% |

On the 12-root Shogi holdouts, the v2 parent’s mean/median teacher action
regret was 185.27/140 on D0, 40.50/1 on D1, and 4.25/0 on D2. The v4
comparator was 382.82/381, 104.83/20, and 40/1 respectively. Thus the
learner-facing policy risk is distribution-sensitive and is not described by
one global scalar-fit number.

The diagnostic correlations also show why root score error is only a partial
proxy. Pearson/Spearman correlation of root 2k score error with v2 action
regret was D0 0.32/0.11, D1 0.17/0.44, and D2 -0.10/0.54. Correlation of the
teacher action gap with v2 regret was D0 -0.08/-0.36, D1 -0.08/0.35, and D2
-0.15/0.17. The signs and magnitudes are not stable enough to gate policy
quality with MSE or a single root-score error statistic.

### Shogi fixed-representation objective comparison

The three objectives used the same architecture and three seeds. Primary
metrics are action regret, top-1 action, and pairwise ranking; MSE and soft
cross-entropy/KL are secondary.

| Distribution/objective | Mean regret by seed | Top-1 by seed | Ranking by seed |
| --- | --- | --- | --- |
| D0 pointwise Q | 264.45 / 326.27 / 265.27 | .364 / .273 / .273 | .507 / .493 / .498 |
| D0 pairwise | 272.00 / 237.27 / 272.00 | .182 / .273 / .182 | .546 / .556 / .541 |
| D0 soft policy | 562.45 / 539.64 / 179.64 | .091 / .091 / .182 | .507 / .517 / .517 |
| D1 pointwise Q | 1.83 / 15.00 / 30.42 | .500 / .333 / .500 | .660 / .655 / .634 |
| D1 pairwise | 29.58 / 2.17 / 30.92 | .583 / .583 / .583 | .664 / .690 / .685 |
| D1 soft policy | 40.50 / 39.00 / 10.92 | .500 / .417 / .500 | .056 / .375 / .000 |
| D2 pointwise Q | 881.00 / 1048.00 / 1046.67 | .333 / .250 / .333 | .624 / .597 / .667 |
| D2 pairwise | 706.67 / 707.50 / 707.50 | .750 / .667 / .667 | .726 / .715 / .715 |
| D2 soft policy | 316.42 / 638.08 / 336.92 | .500 / .333 / .333 | .511 / .479 / .043 |

The result supports an objective-to-policy mismatch diagnosis. Pointwise
fitting is not a reliable policy gate; pairwise ranking can improve top-1 or
ranking without consistently minimizing regret; and soft policy distillation
does not guarantee ranking quality. The D0 soft objective is especially poor,
while D1/D2 behavior changes with the state distribution. These are small
diagnostic samples, not a strength claim.

### D1/D2 overlap sensitivity

The full Shogi position-key overlap matrix is:

|  | D0 | D1 | D2 |
| --- | ---: | ---: | ---: |
| D0 | 36 | 0 | 0 |
| D1 | 0 | 36 | 17 |
| D2 | 0 | 17 | 36 |

D1 and D2 therefore share 17/36 roots. Excluding shared roots leaves 19
unique roots in each distribution; frozen dev/holdout membership is unchanged.
On those unique roots, D1 v2 regret is mean 212.21 (median 0), versus D2 mean
1.11 (median 0). The corresponding v4 means are 216.11 and 34.00. Any
D1-versus-D2 conclusion is consequently labelled
`EXPLORATORY_CORRELATED_SAMPLES`, not a causal distribution comparison.
`scripts/f59_overlap_sensitivity.py` computes and regression-tests this
sensitivity check.

### Western sanity diagnostic

The 12-root diagnostic-only Western run produced:

| Distribution | Stable roots | Candidate actions (mean) | Legal actions (mean) | 10k→20k | 40k→80k | v2 2k→80k |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| D0 random | 11/12 (91.7%) | 6.33 | 30.08 | 91.7% | 91.7% | 58.3% |
| D1 self-play | 12/12 (100%) | 6.58 | 33.92 | 100% | 33.3% | 16.7% |
| D2 PV corridor | 12/12 (100%) | 6.33 | 29.75 | 100% | 58.3% | 33.3% |

This is consistent with the Shogi warning that budget-dependent action
stability can remain poor even when a cheaper teacher comparison is stable.
It is a sanity signal only; no Western objective or cross-game deployment
conclusion is drawn.

## Answers to the F59 questions

1. **Is the teacher action surface stable?** Mostly at 10k→20k, but not at
   the larger root budget: Shogi is 77.8–88.9% at 40k→80k for D1/D0, and
   Western D1 is 33.3%. Therefore the classification is a mixture including
   `TEACHER_POLICY_SURFACE_UNSTABLE` for budget-sensitive use.
2. **Does MSE predict policy regret?** Not reliably. Score-error and gap
   correlations vary by distribution and rank statistic; MSE remains
   secondary.
3. **Does the state distribution matter?** Yes, the policy-relevant surfaces
   differ in baseline regret, gaps, legal-action counts, and budget stability.
   The supported classification is `POLICY_RELEVANT_DISTRIBUTION_DIFFERS`,
   with the D1/D2 comparison restricted to exploratory correlated samples.
4. **Is there objective mismatch?** Yes:
   `VALUE_TO_POLICY_OBJECTIVE_MISMATCH_SUPPORTED`. Fixed-representation
   pointwise, pairwise, and soft objectives trade off regret, top-1, and rank
   differently, and lower scalar-fit loss is not a deployment guarantee.
5. **Does this make representation the primary issue?** No. F58 already showed
   that nonlinear value capacity alone could improve intermediate fit while
   damaging policy transfer; F59 now supplies stronger T1–T3 evidence.
   `REPRESENTATION_REMAINS_PRIMARY` is not supported.
6. **What is the next route?** Hold evaluator/CNN/native redesign. First run a
   larger, disjoint, learner-distribution experiment with policy-regret and
   ranking gates, then paired strength tests. Only after those gates pass
   should representation capacity or runtime redesign be revisited.
7. **Go/no-go?** No-go for deployment or promotion. F59 is a diagnostic
   checkpoint, not a candidate release.

## Regression and artifact boundary

The durable implementation is in
[`f59_action_spectrum_diagnosis.py`](../../scripts/f59_action_spectrum_diagnosis.py),
[`f59_overlap_sensitivity.py`](../../scripts/f59_overlap_sensitivity.py), and
[`test_f59_action_spectrum_diagnosis.py`](../../tests/test_f59_action_spectrum_diagnosis.py).
Raw JSON results, generated binaries, and transient flow evidence remain
outside Git as required by the repository policy. The regression suite checks
perspective sign, total-Q pairwise ranking, fixed-objective finiteness, frozen
split behavior, and overlap sensitivity.
