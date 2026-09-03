# H50/F52 block-preconditioned TD child and arena

Parent checkpoint: `da416199b89406c81471d236acc3c4701175d639`.

F52 froze semantic RuleSet execution, TT, root parallelism, state transport,
evaluator features, and fixed-point representation.  It used the current-v2
parent reconstructed with dynamic weights `(2, 3, 5)`, two self-play
trajectories, TDLeaf `(alpha=0.05, lambda=0.7)`, and one generic update rule:
for each nonzero board, hand, or dynamic TD block, preserve its internal
direction and set its L2 norm to 5% of the parent block norm.  Zero-gradient
blocks were copied unchanged.

## Disjoint holdout

The holdout was `S49-M[16:32]`, disjoint from the 16 F51 positions.  Teachers
were built from the same current-v2 parent at 20k, 40k, and 80k nodes; the
40k-to-80k stability gate passed for both rulesets.

| RuleSet | 20k vs 40k | 40k vs 80k | Parent agreement | Natural child agreement | Preconditioned child agreement | Preconditioned move flips | Natural mean abs score displacement | Preconditioned mean abs score displacement | Classification |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Western Chess | 68.75% | 93.75% | 43.75% | 43.75% | 37.5% | 31.25% | 9.9375 | 16918.25 | `F51_PRECONDITIONING_SIGNAL_DID_NOT_GENERALIZE` |
| Standard Shogi | 68.75% | 100.0% | 68.75% | 68.75% | 68.75% | 0% | 58.4375 | 28560.875 | `F51_PRECONDITIONING_SIGNAL_DID_NOT_GENERALIZE` |

The F51 5% signal did not generalize to this disjoint holdout.  Western's
preconditioned child was Native-effective and changed 5/16 decisions, but
agreement fell by 6.25 percentage points.  Shogi's preconditioned child was
Native-effective but changed no holdout decision and did not improve
agreement.  Therefore the arena gate failed independently for both rulesets;
no 8-pair arena or 32-pair confirmation arena was run.

## Exact floating-point parameter deltas

The following are `child - parent` deltas, emitted without re-rounding by the
experiment.  They are reported for both the natural and preconditioned
children; dictionary keys identify the evaluator parameters.

### Western Chess

Natural:

```text
board: B=0.0, N=-2.6042485387733905e-05, P=1.5665782018947638e-05, Q=-4.560259640129516e-06, R=-1.0426153949083528e-05
hand: B=6.245223175938008e-06, N=4.843517444896861e-06, P=6.939136820705016e-09, Q=1.523140554127167e-05, R=9.13190410756215e-06
dynamic: anchor_safety=-0.0008186076146303733, mobility=-0.0024612120167994966, promotion_potential=5.60039540493662e-05
Native scale=256; board delta=[0,0,0,0,0,0]; hand delta=[0,0,0,0,0,0]; dynamic delta=[-1,0,0]
```

Preconditioned:

```text
board: B=0.0, N=-124.88254212004153, P=75.1227332451948, Q=-21.867990251615538, R=-49.996941164061354
hand: B=44.999999818540005, N=34.8999992476198, P=0.04999999949972156, Q=109.75000048583343, R=65.79999971282064
dynamic: anchor_safety=-0.09725313543901493, mobility=-0.29239965685148284, promotion_potential=0.006653444252094687
Native scale=256; board delta=[0,0,-31970,19231,-5598,-12799]; hand delta=[11520,0,8934,13,28096,16845]; dynamic delta=[-75,2,-25]
```

### Standard Shogi

Natural:

```text
board: B=2.379307807132136e-05, G=-3.937437440981739e-06, L=-2.423577734589344e-05, N=2.6761945775888307e-05, P=-0.0002706072929186121, R=4.2708688852144405e-05, S=-5.150227480044123e-07, TB=5.1711835567402886e-05, TL=0.0, TN=-9.602764862393087e-06, TP=0.00014288439558640675, TR=0.00012475769972297712, TS=3.754354747798061e-05
hand: B=0.00015707318425484118, G=-3.510756823743577e-05, L=-0.00019482906378698317, N=-0.0002140230497786888, P=-0.0005154365680084538, R=0.00032344667215511436, S=-0.00018153118890040787, TB=8.513446050528728e-05, TL=3.986525211985281e-05, TN=3.986525211985281e-05, TP=3.986525211985281e-05, TR=0.00010745900181063917, TS=3.986525211985281e-05
dynamic: anchor_safety=-0.0016906651403809647, mobility=-0.043855179100175556, promotion_potential=-0.0005479551177813846
Native scale=256; board delta=[0,0,0,0,0,0,0,0,0,0,0,0,0,0]; hand delta=[0,0,0,0,0,0,0,0,0,0,0,0,0,0]; dynamic delta=[-11,0,0]
```

Preconditioned:

```text
board: B=17.217622495048317, G=-2.849287143659012, L=-17.537977388415356, N=19.366013855835945, P=-195.82225552798573, R=30.905714666696895, S=-0.3726910500995473, TB=37.4207515587791, TL=0.0, TN=-6.948944554957961, TP=103.39686089649626, TR=90.2796590984126, TS=27.16801187568626
hand: B=47.715790346717995, G=-10.664999080191137, L=-59.18529509164455, N=-65.01605618458927, P=-156.57964364063744, R=98.25683276310974, S=-55.145658325159616, TB=25.862199763904073, TL=12.110291271511642, TN=12.110291271511642, TP=12.110291271511642, TR=32.64396291186813, TS=12.110291271511642
dynamic: anchor_safety=-0.0118725001212594, mobility=-0.307967915555031, promotion_potential=-0.0038479513458460346
Native scale=256; board delta=[4408,-729,0,-4490,4958,-50130,7912,-95,9580,0,-1779,26470,23112,6955]; hand delta=[12215,-2730,0,-15151,-16644,-40084,25154,-14117,6621,3100,3100,3100,8357,3100]; dynamic delta=[-79,-1,-3]
```

## Generated RuleSet sanity

The same generic 5% block-preconditioning construction executed on generated
semantic `weird_0`: Native executable `true`, action present `true`, and TD
positions `2`.  No production RuleSet or search infrastructure was changed.

Transient JSON and console output remain under
`.generic_chess_flow/f52-block-preconditioned-td-child-and-arena/` and are
not tracked.
