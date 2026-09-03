# H50/F51 learning direction and target diagnosis

Parent checkpoint: `6516971faadd577a482f025f9b72137f0dce78d5`.

F51 froze the F50 semantic search and five-block evaluator representation:
material board, material hand, mobility, promotion potential, and anchor
safety.  The fixed F49 S49-M 80,000-node results were used as the teacher;
the 16-position stable subset was measured at 2,000 nodes with eight workers.
Teacher action strings were normalized against candidate action dictionaries
before calculating agreement.

## Actual TD child and normalized direction

The actual two-trajectory TD children were effectively different in Native,
but their natural steps produced no move flips:

| RuleSet | Parent teacher agreement | Natural child agreement | Natural move flips | Effective Native dynamic delta | Classification |
| --- | ---: | ---: | ---: | --- | --- |
| Western Chess | 25.0% | 25.0% | 0/16 | mobility -1; promotion 0; anchor 0 | `TD_DIRECTION_GOOD_STEP_TOO_SMALL` |
| Standard Shogi | 62.5% | 62.5% | 0/16 | mobility -11; promotion 0; anchor 0 | `LOCAL_EVALUATOR_CAPACITY_STILL_LIMITING` |

Natural TD floating dynamic deltas were Western `(-0.0024612120,
+0.0000560040, -0.0008186076)` and Standard Shogi `(-0.0438551791,
-0.0005479551, -0.0016906651)`.  Their dynamic-direction cosine with the
best local dynamic finite-difference direction was `0.9487` and `0.9992`,
respectively.  The natural child changed Native scores but did not change
the selected move on the stable corpus.

The board/hand floating TD deltas were also nonzero, but the observed child
updates remained below the 1/256 Native quantum for both RuleSets.  This is a
resolution observation, not a hidden-child issue: the effective dynamic
delta proves that the actual child evaluator was distinct.

## Evaluator-norm TD direction surface

The actual TD direction was normalized independently within board, hand, and
dynamic blocks and applied at 0.5%, 1%, 2%, 5%, and 10% of each block's parent
norm.  The rows below report `flip rate / teacher best-move agreement / teacher
score-ranking agreement`:

| RuleSet | 0.5% | 1% | 2% | 5% | 10% |
| --- | --- | --- | --- | --- | --- |
| Western Chess | 12.5% / 31.2% / 75.6% | 31.2% / 31.2% / 76.8% | 37.5% / 37.5% / 78.0% | 37.5% / 37.5% / 75.6% | 43.8% / 37.5% / 67.1% |
| Standard Shogi | 0% / 62.5% / 79.3% | 0% / 62.5% / 79.3% | 0% / 62.5% / 79.3% | 12.5% / 62.5% / 78.3% | 31.2% / 50.0% / 75.0% |

Western therefore has a useful TD direction once its magnitude is placed in
the evaluator's local scale, while the natural step is too small to expose
that leverage.  Standard Shogi changes decisions at larger amplitudes but
does not improve agreement with this fixed teacher.

## Local dynamic finite differences

For each dynamic weight, positive and negative perturbations at 1%, 5%, and
10% of the dynamic-vector norm were measured.  Western's best local teacher
agreement remained 25.0% (no improvement over parent); Standard Shogi's best
remained 62.5% (no improvement).  The best Western local direction was
negative mobility at 1%, and its alignment with the TD dynamic direction was
0.9487.  No local Standard Shogi dynamic direction improved teacher
agreement.

No arena was run: the natural children had zero decision flips, and the
normalized probes are diagnostic perturbations rather than trained children.
No external AlphaSho comparison is warranted.

## Conclusion

F51 rules out the previously suspected quantization noop.  Western's TD
direction is strongly aligned with a teacher-improving local direction, but
the natural update is too small; the next minimal intervention should be
update normalization or learning-rate magnitude.  Shogi's TD direction is
also aligned internally, but its local dynamic perturbations do not improve
the fixed teacher, so target/credit assignment remains unresolved there.  The
representation and search infrastructure remain frozen for this diagnosis.

Transient F51 JSON output remains under
`.generic_chess_flow/f51-learning-direction-target-diagnosis/` and is not
tracked.
