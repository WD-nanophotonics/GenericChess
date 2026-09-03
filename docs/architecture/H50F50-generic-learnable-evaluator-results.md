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
new evaluator without recompiling the RuleSet.  Semantic v2 binds the full
board/hand/dynamic parameter vector as 256x fixed-point integers; Native uses
64-bit accumulation and clamps ordinary static scores below the mate-score
band.  Thus sub-unit learned changes are observable whenever they cross a
fixed-point quantum, while the historical material-only quantization path is
unchanged.

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

## Initial TD learning and arena (superseded for learning inference)

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

This initial arena result is retained as provenance only.  Its TD children
were passed through the old integer Native quantization, so the small learned
changes were not guaranteed to reach the evaluator.  It is not evidence for
an objective/credit-assignment bottleneck.

Generated semantic sanity also passed on `weird_0` (fingerprint
`981d65092469ba8dba6f539f45ea353d2c4063125ff57d385d0a4d8f208d3704`): Native
search selected an action, returned dynamic features `(5, 0, 5)`, and TD
executed on two positions.

## Corrective effective-weight resolution and arena gate

Corrective work order
`GENERICCHESS-F50-CORRECTIVE-EFFECTIVE-LEARNED-WEIGHT-RESOLUTION-AND-ARENA-RERUN`
used parent `0abe9c34fbf25fe37df80da6e0ededa348eac24d`.  The actual Western
and Standard Shogi TD children were inspected before any arena.  The exact
floating checkpoint deltas and the exact Native-bound deltas were:

| RuleSet | Floating dynamic delta | Native dynamic delta | Native board/hand delta | Stable-corpus flips |
| --- | --- | --- | --- | ---: |
| Western | mobility -0.0024612120; promotion +0.0000560040; anchor -0.0008186076 | mobility -1; promotion 0; anchor 0 | all 0 at 256x | 0/16 |
| Standard Shogi | mobility -0.0438551791; promotion -0.0005479551; anchor -0.0016906651 | mobility -11; promotion 0; anchor 0 | all 0 at 256x | 0/16 |

The complete floating board/hand delta vectors were nonzero at these entries
(omitted entries were exactly zero): Western board `N=-0.0000260425,
P=+0.0000156658, Q=-0.0000045603, R=-0.0000104262`; Western hand
`B=+0.0000062452, N=+0.0000048435, P=+0.0000000069,
Q=+0.0000152314, R=+0.0000091319`; Standard Shogi board
`B=+0.0000237931, G=-0.0000039374, L=-0.0000242358,
N=+0.0000267619, P=-0.0002706073, R=+0.0000427087,
S=-0.0000005150, TB=+0.0000517118, TN=-0.0000096028,
TP=+0.0001428844, TR=+0.0001247577, TS=+0.0000375435`; Standard
Shogi hand `B=+0.0001570732, G=-0.0000351076, L=-0.0001948291,
N=-0.0002140230, P=-0.0005154366, R=+0.0003234467,
S=-0.0001815312, TB=+0.0000851345, TL=+0.0000398653,
TN=+0.0000398653, TP=+0.0000398653, TR=+0.0001074590,
TS=+0.0000398653`.

The floating board/hand deltas were nonzero in both children but smaller than
one 1/256 Native quantum in this TD step.  They were still reported and did
not silently enter the arena as if effective.  The dynamic changes did cross
the fixed-point quantum, proving that the child evaluator differs from its
parent.  The stable corpus mean score differences were +4.8125 (Western) and
+11.6875 (Standard Shogi) in fixed-point score units.

Because the natural TD child produced no move flips, the deterministic TD
direction amplitude surface was measured instead of running an arena:

| RuleSet | Amplitudes tested | Move-flip rate at every amplitude |
| --- | --- | ---: |
| Western | 0.25, 0.5, 1, 2, 4 | 0/16 |
| Standard Shogi | 0.25, 0.5, 1, 2, 4 | 0/16 |

Per the corrective gate, no 8-pair arena was run because the actual child did
not measurably change decisions.  The result separates direction from step
size: the natural TD direction changes Native scores and dynamic parameters,
but has no stable-corpus decision leverage at amplitudes through 4x.  No
strength claim is made.

## Conclusion

F50 changes the diagnosis from material-only representation limiting to an
expressive-enough generic evaluator representation: the prescreen moves
Native decisions on both primary RuleSets, and the corrective run proves that
actual TD children can change the Native evaluator rather than being erased
by integer quantization.  The natural TD direction nevertheless has zero
stable-corpus decision flips through 4x, so the remaining question is TD
target/credit assignment or update normalization—not representation
capacity—and no arena-strength conclusion is justified yet.  The dynamic leaf
evaluator is moderately more expensive because it computes both owners'
guarded generic action counts, but the observed cost remains acceptable for
the next learning iteration.

Transient experiment outputs remain under
`.generic_chess_flow/f50-generic-learnable-evaluator/` and are intentionally
not tracked.
