# Leaper world adaptation and material-depth controls

DEV_AUX / sidemission. Shared infrastructure is the committed sandbox revision
`d1017250c8720113000105b7519f6beffa774d0a`. All 238 shared package files (including 199 Python files)
match it; only the existing two AUX learner modules are additional. Its profile
cache representation fix and tests were imported unchanged. This is source
reuse, not a measured acceleration claim. Oracle labels stay outside training.

Short experience changes with the world, but does not reliably reach its better
decision regions. New ABA and vertical-C training retains initial-condition
dependence. In the vertical world, every final model is provably worse than an
already known frozen parameter region, even without filling any missing label.
These are finite, exposed-world results; retraining in another known world is
not a held-out validation of a general learning law. At the same completed D6,
frozen TD still lowers errors from136to120 in ABA and403to258 in ABC for
less than0.83% more nodes; deeper search does not erase that finite advantage.

## A count-matched geometry intervention

The previously selected fresh four-actor board is retained exactly:

```
K1 A1  .
 .  . K0
 .  . C0
```

Only C changes from horizontal to vertical. One shared-Core graph completes
1,072 vertices / 2,424 edges in 1.065 seconds, below the declared 10,000-state /
60-second graph and 120-second whole allowances. Existing horizontal and
C-absent results are reused; no graph or old label stage is topped up.

| Fresh setup | Optimal root | Shared K0 c1-b0 action |
|---|---|---|
| Horizontal C present | DRAW | LOSS |
| C absent | DRAW | DRAW |
| Vertical C present | DRAW | DRAW |

The vertical root has just that one legal action. Literal Core continuation
`K0 c1-b0, A1 b2-b1, K0 b0-a0, K1 a2-b2, C0 c0-c1, A1 b1-a1`
leaves the legal drawing escape `K0 a0-b0`. In the earlier horizontal winning
certificate, C instead moves c0-b0 and occupies that escape square; A1 b1-a1
is then mate. Every displayed vertical choice preserves its full-prefix draw
label. This explains a concrete action-conditional liability. Optimal root WDL
does not change, so this is not a negative intrinsic price or a negative root
contribution. The former 24-ply history is never transplanted into new rules.

## Six new experiential runs

The existing runner now accepts a declared coexistence lineup and C axis.
There is no new learner or rules engine. ABA uses A/B/A per side; ABCv uses
A/B/C with vertical C. Each world receives uniform, plus and minus starts,
32 episodes, eight label-blind legal random openings, alternating learner
colors, and an RNG legal-move opponent. Opening/RNG seeds are 20261022 and
2026102201. Legal walks depend on the world: equal seeds do not make different
worlds' trajectories identical or create a clean path-matched geometry effect.

A=1 is fixed. Plus starts at B=1.03, C=1.01 where present; minus at B=.97,
C=.99. Hands remain unused. Each new arm retains the existing 120-second /
2,000,000-node allowance, D2, eta=.05, lambda=.95, scale=10, and 64-ply
experimental horizon. Closed horizontal runs are not extended.

The runner retains its conservative nine-symbol max-ply bound in ABA too.
Both that bound and the reference ABA graph's tighter seven-symbol bound are
inactive before repeat-two termination. Fresh decision assessment uses the
existing reference world; no ABA training history is transplanted into it.

| World/start | Final B | Final C | Learner W/D/L | Nodes |
|---|---:|---:|---:|---:|
| ABA uniform | .9519516 | absent | 10/22/0 | 4,186 |
| ABA plus | 1.0085529 | absent | 6/26/0 | 4,807 |
| ABA minus | .9224780 | absent | 10/22/0 | 4,186 |
| ABCv uniform | 1.0152779 | .9383662 | 6/26/0 | 3,167 |
| ABCv plus | 1.0445860 | .9618354 | 7/25/0 | 3,272 |
| ABCv minus | .9548883 | .9684087 | 4/28/0 | 3,510 |

All 192 episodes reach actual rule terminals, zero missing/UNKNOWN; the six
runs take 17.76 seconds in total. These dependent training outcomes against a
weak RNG opponent are not independent strength tests. ABA has two episodes per
arm with no learner query: the opponent ends the game before the learner acts.

Independent replay verifies all 192 complete records, 3,844 played edges and
1,930 stored search PVs (3,748 PV edges, 174 terminal PVs). An initial replay
assertion mistakenly used 100,000 instead of the learner's MATE=1,000,000;
the failure is retained, and the corrected replay closes within the original
120-second allowance. No training or search is repeated.

A separate complete-prefix observer evaluates all 96 saved vertical-world
games in 152.72 seconds, within 300 seconds. It uses the identical compiled
fingerprint and actual histories, not fresh-position labels. The learner has
5/7/8 regrets among 277/287/309 actions in uniform/plus/minus runs; their
genuine WDL-choice opportunities number 39/40/37. Cross-run counts reflect
different policy-dependent histories, not a paired causal quality comparison.
None of the 17 winning games contains a detected learner regret. Instead,
16 of the 79 draws contain 20 regrets: eight WIN-to-DRAW and twelve DRAW-to-LOSS
choices, followed by opponent errors that permit recovery. This sample does
not supply a winning-player-error counterexample and does not prove winners
universally play optimally. It does show that the same final draw can conceal
different prior strategic mistakes. No old fresh-label slot is filled.

There is an exact bookkeeping identity on all 96 complete histories:
`learner outcome - initial learner WDL = sum foe WDL gaps - sum learner WDL gaps`.
Each gap is the acting player's best WDL minus its chosen action's WDL; a
WIN-to-LOSS gap would count two. The paired initial colors cancel within each
run. Here the three outcome sums 6/7/4 equal 11-5 / 14-7 / 12-8 exactly;
in total, 17 = 37-20. This locates the payoff in the mutual sequence of errors,
not in an intrinsic piece value. It is a post-hoc identity, not a replacement
reward or a causal attribution of wins to training.

## Exact decision-quality assessment

Post-hoc ideal uniform-tie D2 error uses the existing complete ABA/ABC labels
and the unchanged partial ABCv labels. No exact label enters the learner.
Original ABC runs are included as historical controls, not new replicates.

| New run | Initial to final expected-error contrast, final minus initial |
|---|---:|
| ABA uniform | -223.1 |
| ABA plus | 0 |
| ABA minus | 0 |
| ABCv uniform | [-141.2667, -50.7667] |
| ABCv plus | [-380.3667, -261.3667] |
| ABCv minus | exactly 0 |

ABA uniform ends at 1,809.3 expected errors; minus starts and ends at that
same total. Plus remains at 2,287.8333. None reaches the already known B<.5
region with 1,747.3 errors. Uniform and minus generate the same 32 complete
records and all 335 stored PVs; 98.25% of their initial B separation survives.
There is no evidence of numerical convergence to a unique value.

ABCv ends in the existing local sectors 10, 11 and 7, respectively. Its 2,347
missing action-label records remain missing. As before, existing graph facts
show that every action is optimal at 1,651 of those roots; only 696 can affect
an error contrast. Total-variation bounds on their uniform action sets give:

| Final vertical model minus known sector 8 | Full-domain expected-error bound |
|---|---:|
| Uniform-trained / sector 10 | [181.5, 230.5] |
| Plus-trained / sector 11 | [188.5, 239.5] |
| Minus-trained / sector 7 | [89.75, 104.75] |

All bounds are strictly positive. Thus none of these short vertical runs
reaches even this known better policy region. Sector 8 is not asserted to be
globally optimal. Improvement over one's own initialization and adaptation
to the best available decision region are different claims.
The old horizontal TD leaf order (sector 9) also beats all three new vertical
finals, with strictly positive lower bounds 178.5, 185.5 and 86.75 expected
errors, respectively. These remain ideal uniform-tie comparisons.

## Updates, information and surrogate loss

The 900-second post-hoc observer completes in 636.22 seconds. It assesses all
288 updates across the three old horizontal and six new runs. Among 223
nonzero parameter updates there are 26 complete leaf-order cell changes and
only 20 updates with an identified nonzero change in expected D2 errors.
A cell change need not change decision quality. The other 268 updates have
exactly zero expected-error contrast, including the missing-label bounds.

Frozen-old-PV, frozen-old-target half-squared residual decreases on 208 updates,
increases on 15 and is unchanged on 65. Among the 20 updates with both nonzero
loss and quality changes, signs agree on 12 and disagree on 8. These are
descriptive counts, not independent Bernoulli trials or a significance test.
There are two loss-down/error-up events in the old horizontal uniform run
and four in the new vertical uniform run. No monotone improvement law holds.

TD(lambda)'s eligibility update is a semi-gradient through the saved current
prediction, not a gradient of a re-searched global decision objective. Continuous
weight movement can stay inside a decision plateau; a later boundary crossing
can improve or worsen exact action quality. The residual diagnostic freezes
old PVs and targets and must not be called the objective of a new search.

All six new update trajectories reconstruct exactly from their stored samples.
For ABA uniform, B changes by -.04804845: -.00543909 from nonterminal bootstrap,
-.04220748 from terminal-PV targets, and -.00040187 from final actual outcomes.
For vertical uniform, B changes by +.01527791, primarily +.01762592 from
terminal-PV targets, opposed by small negative bootstrap/final terms. C changes
by -.06163375. World-dependent experience affects the update, but this does
not establish optimal adaptation or a universal bias.

A cheap frozen-path counterfactual checks ten declared B values in [0,8].
ABA uniform/minus paths give negative aggregate B drift at every sampled value;
plus paths change drift sign between .25 and .49. This is not re-searched
training or a convergence proof. It gives no reason to claim an unavoidable
bad fixed point, and no authorization to extend closed training runs.

Cached order-cell representatives were initially printed as final parameter
values in the observer metadata. Error totals and signatures were correct;
the compact result now takes actual initial/final weights from the episodes,
and retains the original metadata privately.

## One prospective opening-coverage intervention

After the short-run failure was observed, one changed-sampling arm was fixed
before execution: ABA uniform, the same 32 episodes and RNG-foe seeds, but 16
openings instead of cycling eight twice. The first eight generated prefixes
match exactly, and the first 16 complete episode records and parameter updates
are identical to the old run. Later episodes introduce the new prefixes.
No labels or outcomes select openings; duplicate and terminal prefixes remain.

Distinct initial histories/Positions increase from 8 to 15, and initial material
vectors from six to seven; one terminal prefix is retained. The new run ends at
B=.9634718 versus the old .9519516. All 15 reachable material-vector orders,
including zero, agree, so its ideal D2 uniform-tie total remains 1,809.3 errors:
there is no additional decision-quality gain. This is an order-based inference,
not a new public-query census or a claim of identical implementation node counts.

The run completes in 2.74 seconds with 12 W / 19 D / 1 UNKNOWN, zero missing
episodes, within its unchanged 120-second/2,000,000-node training allowance.
Episode 24 reaches the 64-ply rollout cap while still ongoing; its final TD
term is withheld and its UNKNOWN is retained. All 32 records replay. Changed
openings and censoring prevent interpreting its training wins as a strength
gain. This single controlled coverage change does not solve the missed-region
problem; it does not justify automatically adding episodes or more arms.

## Material parameters and search cost

The already closed complete censuses supply the following deployed-policy
points. Nodes include iterative deepening; these are matched distributions,
not exact equal-node tests. Oracle-supervised and experiential TD remain distinct.

| World, model | D2 errors / nodes | D4 errors / nodes | D6 errors / nodes |
|---|---|---|---|
| ABA uniform | 2137 / 662,219 | 531 / 3,169,873 | 136 / 9,472,837 |
| ABA supervised | 1866 / 666,642 | 495 / 3,211,825 | 112 / 9,549,952 |
| ABA frozen TD | 1930 / 665,818 | 499 / 3,212,423 | 120 / 9,551,210 |
| ABC uniform | 1799 / 387,033 | 818 / 1,788,400 | 403 / 5,349,781 |
| ABC supervised | 1754 / 389,039 | 853 / 1,807,173 | 392 / 5,391,350 |
| ABC frozen TD | 1326 / 388,636 | 469 / 1,809,870 | 258 / 5,387,246 |

Fitting WDL and optimizing decisions can have opposite rankings across worlds:
at D2 ideal uniform-tie error, supervised beats frozen TD in ABA (1747.3 versus
1809.3), but loses in ABC (1649.9167 versus 1288.5333). The same reversal holds
for the actual D2 public choices and for the complete D4 public choices.
Prediction fit is not a universal decision-quality surrogate.

The new same-D6 material controls complete all 172,630 slots in 3,667.96
seconds (61.13 minutes), within the original 4,500-second cap. They reuse 256
old D6 slots exactly, with zero missing/UNKNOWN and all requests completing D6.
The old uniform-D6 census is reused in full. The imported profile-cache change
is bypassed by the adapter's material evaluator_override and disabled disk
cache; rules, public search, zero-price ordering and actual budgets are shared.
This is a same-depth parameter comparison, not an engine-speed trial.

| Frozen TD versus uniform at D6 | Errors fixed / introduced | Node increase |
|---|---:|---:|
| ABA | 16 / 0 | 0.8273% |
| ABC | 147 / 2 | 0.7003% |

Thus depth does not erase the finite parameter advantage. Its absolute size
shrinks: TD improves errors by 207/32/16 in ABA at D2/D4/D6, and 473/349/145
in ABC. The ABC D6 error reduction is 35.98% for about 0.70% more search nodes;
this does not include training amortization or establish whole-game strength.
ABA has no worse-WDL TD choice on this finite fresh distribution, while ABC
has two regressions, so a universal per-position dominance claim fails.

The supervised-versus-TD ranking reversal persists at D6: supervised wins in
ABA (112 versus120 errors), TD in ABC (258 versus392). Against supervised,
TD improves136 ABC choices and worsens2, but worsens8 ABA choices and improves
none. Relative usefulness depends on world and target, not prediction fit alone.
Deeper search also remains nonmonotone: TD-D6 fixes380/new1 versus TD-D4 in ABA,
and fixes257/new46 in ABC.

All 172,630 selected-action labels independently match the frozen exact labels.
All 11,192 C-absent TD matched pairs agree on action, nodes and WDL. Residual
missed root wins have ranks7..15 in ABC and rank7 in ABA; none has rank<=6.
Losing-action opponent-win ranks are likewise7..15/7. This passes a sufficient
mate-visibility check, not a proof that horizon alone causes every error.
Complete D6 PVs were not exported for an independent second replay; the actual
adapter enforces literal full-history PV admission on every usable query.

Uniform D6 costs about 2.95 times TD-D4 nodes and meets its error count in both
worlds. That is a constructive pair of measured operating points, not an exact
node-equivalent multiplier for learning. D3/D5 and intermediate node budgets
were not censused. No interpolation or Elo conversion is supplied; ordinary
local overlap also limits wall-time interpretation. Old missing/UNKNOWN and
all original caps remain unchanged.

Generated graphs, trajectories, query journals and one-off analysis drivers
remain ignored locally. The compact scientific data and this report contain the closed results;
173 relevant regressions pass. All bounded producers have exited. No
PRIMARY state/defaults, new worker, second rules engine or schedule mutation.

The next information-coverage task has begun with a retained-data inventory.
ABA uniform/plus/minus/coverage16 have 335/387/335/276 complete learner queries,
but only 36/67/36/32 nonterminal chosen PVs with nonzero B gradient support.
All complete prefixes and PV paths remain available. Chosen-PV support is not
all-branch sensitivity, nor does it count eligibility inherited from earlier
observations. The next bounded observer will inspect actual Core D2 alternatives
around the B=1/2 boundary (300 seconds / 50,000 Core nodes), not launch more
training, rerun public requests or select training data from oracle labels.

At the final science checkpoint this segment has 73.19 confirmed effective
research minutes. Administrative publication/transport is excluded; all bounded
producers have exited and the next retained-data question remains executable.
