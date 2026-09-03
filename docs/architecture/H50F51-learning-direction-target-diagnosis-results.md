# H50/F51 learning direction and target diagnosis

Parent checkpoint: `0fbb467325f043b99a6a1ebe863ebfa8def6a93c`.

This corrective run supersedes the earlier diagnostic that used the F49
material-only teacher.  It constructs the teacher from the current F50 v2
parent: current board/hand evaluator state, dynamic weights seeded at
`(2, 3, 5)`, and the same semantic persistent Native search.  The 16-position
S49-M subset was evaluated at 20k, 40k, and 80k nodes; the 80k surface is used
only after the adjacent 40k/80k stability gate passed.  Teacher action strings
were normalized against candidate action dictionaries before calculating
agreement.

## Actual TD child and normalized direction

The actual two-trajectory TD children were effectively different in Native,
but their natural steps produced no move flips:

| RuleSet | Parent teacher agreement | Natural child agreement | Natural move flips | Mean abs Native score displacement | Effective Native dynamic delta | Classification |
| --- | ---: | ---: | ---: | --- | --- |
| Western Chess | 12.5% | 12.5% | 0/16 | 10.1875 | mobility -1; promotion 0; anchor 0 | `TD_DIRECTION_GOOD_STEP_TOO_SMALL` |
| Standard Shogi | 68.75% | 68.75% | 0/16 | 85.9375 | mobility -11; promotion 0; anchor 0 | `TD_DIRECTION_GOOD_STEP_TOO_SMALL` |

Natural TD floating dynamic deltas were Western `(-0.0024612120,
+0.0000560040, -0.0008186076)` and Standard Shogi `(-0.0438551791,
-0.0005479551, -0.0016906651)`.  Their dynamic-direction cosine with the
best local dynamic finite-difference direction was `0.9487` and `0.9992`,
respectively.  The natural child changed Native scores but did not change
the selected move on the stable corpus.

The 40k/80k teacher stability was 93.75% for Western and 100.0% for Shogi
(the 20k/40k values were 31.25% and 68.75%).  The board/hand floating TD
deltas were nonzero, but the observed child updates remained below the 1/256
Native quantum for both rulesets.  This is a resolution observation, not a
hidden-child issue: the effective dynamic delta proves that the actual child
evaluator was distinct.

## Evaluator-norm TD direction surface

The raw probe applies one scalar to the complete board/hand/dynamic TD vector.
The block-preconditioned probe independently normalizes board, hand, and
dynamic blocks.  Both were applied at 0.5%, 1%, 2%, 5%, and 10% of the
corresponding norm.  The rows below report `flip rate / teacher best-move
agreement`:

| RuleSet | 0.5% | 1% | 2% | 5% | 10% |
| --- | --- | --- | --- | --- | --- |
| Western raw | 100.0% / 6.25% | 100.0% / 6.25% | 100.0% / 6.25% | 100.0% / 0% | 100.0% / 0% |
| Western block-preconditioned | 12.5% / 18.75% | 31.25% / 18.75% | 37.5% / 18.75% | 37.5% / 18.75% | 43.75% / 25.0% |
| Standard Shogi raw | 87.5% / 6.25% | 93.75% / 0% | 100.0% / 0% | 100.0% / 0% | 100.0% / 0% |
| Standard Shogi block-preconditioned | 0% / 68.75% | 0% / 68.75% | 0% / 68.75% | 12.5% / 75.0% | 31.25% / 56.25% |

Raw scaling is destructive on this sample: it flips most or all decisions
without improving current-v2 teacher agreement.  Block preconditioning
reduces that damage and exposes a modest Western signal plus a Shogi peak at
5%, but these are diagnostic probes, not trained checkpoints.

## Local dynamic finite differences

For each dynamic weight, positive and negative perturbations at 1%, 5%, and
10% of the dynamic-vector norm were measured.  Western's best local probe was
negative mobility at 10%, reaching 18.75% teacher agreement versus the 12.5%
parent, with 6.25% move flips and mean absolute score change 1612.  Standard
Shogi's best was negative mobility at 1%, with 68.75% agreement versus a
68.75% parent, zero move flips, and mean absolute score change 125.  Their
alignment with the TD dynamic direction was 0.9487 and 0.9992, respectively.

No arena was run in F51 because the normalized probes were diagnostic
perturbations rather than trained children; Western's block-preconditioned
probes and Shogi's 5% probe did satisfy the decision-flip plus teacher-
improvement diagnostic gate.  No external AlphaSho comparison was warranted
at this stage.

## Conclusion

F51 rules out the previously suspected quantization noop.  Both current-v2
natural children are too small to expose a decision change on this corpus.
Western has a weak teacher-improving local direction and Shogi has a narrow
block-preconditioned peak, but neither supports an arena or a trained
checkpoint.  Follow-up should compare step-size/normalization and
credit-assignment choices while keeping search and evaluator infrastructure
frozen.

Transient F51 JSON output remains under
`.generic_chess_flow/f51-learning-direction-target-diagnosis/` and is not
tracked.
