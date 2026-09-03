# H50/F50 generic learnable evaluator expansion

Parent checkpoint: `b7bbfbefb5e0f46a4797eaa843623ddbf2b7e858`.

## Representation

The learnable value now retains RuleSet-specific board and hand weights and
adds the fixed generic dynamic vector:

* `mobility`: legal control count difference;
* `promotion_potential`: promotion-action count difference;
* `anchor_safety`: anchor-action count difference with the existing generic
  check-pressure term.

The semantic Native leaf evaluator and the Python trajectory path use the
same Native feature helper.  The vector is available for Western Chess,
Standard Shogi, and generated semantic RuleSets.  Material-only checkpoints
omit the new field and retain their v1 identity and behavior.  A checkpoint
rebind creates a fresh semantic engine capsule, so the TT is empty under the
new evaluator without recompiling the RuleSet.

## Leverage pre-screen

The accepted F49 S49-M corpora were replayed at 2,000 nodes/search, using 16
positions per primary RuleSet and eight concurrent workers.  The parent was
the material-only checkpoint; each dynamic direction was tested alone and
all three jointly.

| RuleSet / direction | Move-flip rate | Mean score change | Mean dynamic value | Native NPS |
| --- | ---: | ---: | ---: | ---: |
| Western / mobility | 0.6875 | -10.8125 | 0.375 | 1402.8 |
| Western / promotion potential | 0.0625 | 0.8125 | 0.000 | 1403.4 |
| Western / anchor safety | 0.5625 | -7.6875 | -3.750 | 1409.4 |
| Western / joint v2 | 0.6875 | -17.7500 | -3.375 | 1409.1 |
| Standard Shogi / mobility | 0.7500 | -2.5000 | -4.375 | 1081.8 |
| Standard Shogi / promotion potential | 0.3750 | -0.5625 | -0.1875 | 1068.9 |
| Standard Shogi / anchor safety | 0.6250 | -1.8750 | -2.500 | 1071.4 |
| Standard Shogi / joint v2 | 0.6875 | -3.8750 | -7.0625 | 1068.5 |

Dynamic features therefore have usable decision leverage on both primary
RuleSets.  The measured Native evaluator cost was within roughly 0.5% of the
material-only surfaces in this sample (measurement noise); the reachable
depth was unchanged.

## TD learning and arena

TDLeaf was run for two self-play trajectories per primary RuleSet with the
F50 seeded weights `(mobility=2, promotion_potential=3, anchor_safety=5)`.
The learned dynamic weights moved coherently but modestly:

* Western: `(-0.00246, +0.000056, -0.000819)`;
* Standard Shogi: `(-0.04386, -0.000548, -0.00169)`.

The initial paired arena used two openings, 300 nodes/move, depth 6, and
two independent workers.  Each pair used identical openings with colors
swapped and fresh parent/child engines:

| RuleSet | Pair count | Wins | Draws | Losses | Mean child pair score | Bootstrap interval |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Western Chess | 2 | 0 | 4 | 0 | 0.5000 | [0.5000, 0.5000] |
| Standard Shogi | 2 | 2 | 0 | 2 | 0.5000 | [0.5000, 0.5000] |

The child did not beat the parent on either RuleSet.  No larger confirmation
arena was warranted after the flat initial result.

Generated semantic sanity also passed on `weird_0` (fingerprint
`981d65092469ba8dba6f539f45ea353d2c4063125ff57d385d0a4d8f208d3704`): Native
search selected an action, returned dynamic features `(5, 0, 5)`, and TD
executed on two positions.

## Conclusion

F50 changes the diagnosis from material-only representation limiting to an
expressive-enough generic evaluator representation: the new features move
Native decisions on both primary RuleSets and TD updates change their weights
in the intended linear chain.  The remaining bottleneck is not evaluator
leverage but learning signal/credit assignment or the target objective;
arena strength is flat at this small sample.  The dynamic leaf evaluator is
moderately more expensive because it computes both owners' guarded generic
action counts, but the observed NPS cost is acceptable for the next learning
iteration.

Transient experiment outputs remain under
`.generic_chess_flow/f50-generic-learnable-evaluator/` and are intentionally
not tracked.
