# Leaper parameter regions, composition and learning

DEV_AUX, 2026-10-22 JST. Shared infrastructure is pinned to sandbox
`5442b3c1d3a51398d1bfcdd403ee1a825c22c6db`. Its only package change since
the preceding study clarifies a conservative native-admission comment; that
committed change is imported. Core, rules, terminal/history, GameSession and
public q0 search are reused. No second move generator or deployed search is
introduced. The two existing AUX learner modules remain the only additional
package modules. Numerical evidence: [curated data](data/leaper_parameter_regions_20261022.json).

The main result is a concrete, count-matched reversal of useful B coefficients
when horizontal C is replaced by orthogonal A. This is about finite-search
decisions, not intrinsic prices. A broader exact-position census also separates
supervised WDL fitting, public policy quality and experiential parameter drift.

## Matched composition mechanism

The rules use 3x3, capture removal, no drops/promotion/pass, repeat-two DRAW,
stalemate DRAW and shared Core Anchor/checkmate legality. K has eight adjacent
Leaper targets, A four orthogonal targets, B four diagonal targets and C two
horizontal targets. The positive whole-game clock exceeds the complete finite
Position bound, so repetition or ordinary termination occurs first.

Map each ABC Position to the same owner/squares/turn with every C replaced by
A. Both inventories have exactly the same number of actors and occupied cells.
Among 30,985 matched ongoing fresh-history contexts, 4,680 exact WDL values
change. There are 23,994 distinct ABA counterparts: this mapping is many-to-one,
not a population of independent games. Two D1 and two D2 contexts have robustly
opposite low/high B effects. Robust means **every** heuristic-best action is
better/worse in exact WDL, so these reversals do not depend on choosing a
convenient member of a heuristic tie. The four contexts are not four independent
rules. Existing actual common-history diagnostics are a separate comparison.

The 11,192 C-absent matches form a useful negative control: exact labels and
both endpoint action sets agree. Across uniform/closed-TD, D1/D2, all 44,768
saved public comparisons also have identical actions AND node counts. An unused
C type/catalog entry is not evidence of a changed deployed policy here.

One D1 witness, with coordinates (file,rank) beginning at zero:

| Rank | file 0 | file 1 | file 2 |
|---|---|---|---|
| 2 | C1 | B0 | K1 |
| 1 | A0 | empty | empty |
| 0 | K0 | B1 | C0 |

The ABA counterfactual replaces C0/C1 by A0/A1. Side 0 moves; both Anchors are
safe in both actual freshly compiled games. A=C=1 and only B changes.

| World | Exact root | D1 B=.25 | D1 B=1 | D1 B=3 | D2 B=.25 / 3 |
|---|---|---|---|---|---|
| ABA | WIN | WIN | DRAW | DRAW | WIN / WIN |
| ABC | WIN | DRAW | WIN | WIN | DRAW / DRAW |

Low B chooses A(0,1)x(0,2); high B chooses K(0,0)x(1,0). The same physical
capture preferences have opposite strategic consequences after the declared
geometry/composition change. Separate actual GameSessions give fresh fingerprints
`d07e5b159474311c2a95842767c6da95015c44b57b605b67380020d9bc68c3c0`
and `bc731af19c8fcccd4a9b7d3b4ce32289bde642ae32cd7b866e4c213c8e6f24e3`.
The complete cached physical graphs are rebound to those constructors; all
other rule fields are checked unchanged. Actual Core all-defense certificates
prove the two root wins at ranks 3/11, visiting 6/22 nodes respectively.

The resource curve reuses eight D1/D2 calls and adds 28 calls at requested
D3/4/6/8/10/11/12, with 100k nodes/3 seconds each and a 120-second whole cap.
It costs 78,006 new nodes and 23.30 seconds. ABA acts optimally from D2 onward.
ABC with high B selects a winning-valued action at D1, a draw-valued action at
D2 through D10, then a winning action at D11; low B selects draws through D10
and a win at D11. Thus this individual decision-quality curve is not
monotone. Both D12 requests retain UNKNOWN: the search completed an internal
D11 iteration but its PV replay exceeded the original query allowance. There
are 36 records, zero missing, 34 usable results and two UNKNOWN; the separate
D11 results and exact certificates do not refill the D12 slots.

A second, D2 witness fixes K0(0,0), K1(2,0), A0(1,1), B0(2,1), A1(0,2),
C1(1,2), and replaces only that C1 by A1. Here the exact roots are DRAW/WIN,
not WIN/WIN. D2 low/high B yields DRAW/LOSS in ABA and DRAW/WIN in ABC.
Both freshly compiled games and twelve public D1/D2 calls verify this distinction;
the ABC root has a rank-5 Core win certificate. A verifier initially inherited
the first witness's WIN/WIN assumption and stopped before queries. Its failure
and source remain saved; correction reused the original 120-second deadline,
including recovery, finishing in 60.50 seconds. No old evaluation was changed.

Isolating the two C actors clarifies the first witness. Keep the ABC type
catalog, every occupied square/owner and both coefficient settings fixed;
replace only own C0 or only opposing C1 by A. The two endpoints reuse complete
graphs, while the intermediate worlds require new Core graphs of 31,320 and
13,783 Positions. All four finish in 52.12 seconds under a 300-second whole
allowance, each graph capped at 120 seconds/200k Positions. Four identical
both-C queries are reused. The neither-C catalog control exactly matches the
earlier ABA actions and node counts.

| Horizontal C actors retained | Exact root | D1 low / high B | D2 low / high B |
|---|---|---|---|
| neither | WIN, rank 3 | WIN / DRAW | WIN / WIN |
| own C0 only | DRAW | DRAW / DRAW | DRAW / DRAW |
| opposing C1 only | WIN, rank 3 | WIN / WIN | WIN / WIN |
| both | WIN, rank 11 | DRAW / WIN | DRAW / DRAW |

After the low-B capture A(0,1)x(0,2), the opponent's complete reply set is
B(1,0)->(0,1) or (2,1). With the own extra actor still A, A(2,0)->(2,1)
checkmates after either reply, exactly as the actual Core certificates show.
Horizontal C0 lacks that vertical move. Thus the root/decision differences
have a concrete geometry mechanism, not a nominal type-count explanation.
Replacing the opposing actor alone makes both D1 capture choices winning;
replacing the own actor alone leaves both drawing. The price preference at
the two endpoints therefore cannot be attributed to one scalar "C price".
These are four targeted fresh-game counterfactuals, not independent samples.

## All reachable Positions, with explicit history reset

The complete original-layout graphs have 57,437/36,199 ABA/ABC Positions;
52,456/33,859 are ongoing. Every ongoing Position is included, resetting its
history to one occurrence. These are constructed **fresh-history observer
GameSessions**, not replays of the original starting game or all possible
arrangements. The public API has no arbitrary-position reset; the research
constructor binds Core's fresh state and its search witnesses together. A
regression compares this observer with independently compiled real fresh games
for side-0 positions. Side-1 observers remain explicitly constructed states.

Fresh child WDL alone is not a safe action label: returning to the parent may
already draw. Full blocked-parent attractors correct action labels at 540/537
Positions. A rank argument avoids recomputation when every winning continuation
has a rank-decreasing certificate that avoids the parent; uncertain cases use
the full attractor. Three hundred cyclic-graph controls compare the shortcut
with independent root blocking, alongside actual complete-history Core tests.
For example, naive child labels would misclassify 57 ABC uniform-D2 selected
actions as optimal; the corrected observer records their actual regret.

Every one of the 517,890 three-model public queries completes its requested
D1/D2 depth: 0 UNKNOWN, 0 missing, 443.23 seconds under a 3,600-second cap.
All selected actions belong to the literal Model.raw minimax action sets on
the cached Core transitions. There is no oracle lookup in the searcher.

| World / positions | Uniform D1 / D2 errors | Oracle-supervised D1 / D2 | Closed TD D1 / D2 |
|---|---|---|---|
| ABA / 52,456 | 3,790 / 2,137 | 3,474 / 1,866 | 3,474 / 1,930 |
| ABC / 33,859 | 2,550 / 1,799 | 2,574 / 1,754 | 2,271 / 1,326 |

ABC TD versus uniform at D2 fixes 484 previously erroneous choices and introduces
11 errors. There are 486 strict WDL improvements and 11 regressions: two
improvements remain below the exact best WDL. Of 2,215 changed actions, 1,718
have unchanged WDL. Improvements, error fixes, action changes and parameter
changes are therefore different quantities. This is an exposed finite decision
census, not held-out generalization or an actual terminal-game strength result.

The broad B-axis public curve completes all 2,244,190 slots, with zero UNKNOWN
or missing, in 1,771.70 seconds under its unchanged 3,600-second allowance.
It reuses 172,630 uniform B=1 calls and pays 16,719,547 new nodes for the other
2,071,560 calls. Its inputs are seven open leaf-order regions and six boundaries in
0<B<8, with A=C=1; cuts are .5,1,1.5,2,3,4. A representative's public tie choice
and cost are measured, not inferred for every floating-point value in a cell.

| B region / tested point | ABA D1 | ABA D2 | ABC D1 | ABC D2 |
|---|---:|---:|---:|---:|
| (0,.5) / .25 | 3,474 | 1,866 | 2,574 | 1,775 |
| .5 | 3,474 | 1,872 | 2,574 | 1,761 |
| (.5,1) / .75 | 3,474 | 1,930 | 2,574 | 1,754 |
| 1 | 3,790 | 2,137 | 2,550 | 1,799 |
| (1,1.5) / 1.25 | 4,053 | 2,400 | 2,530 | 1,765 |
| 1.5 | 4,053 | 2,400 | 2,530 | 1,765 |
| (1.5,2) / 1.75 | 4,053 | 2,400 | 2,530 | 1,765 |
| 2 | 4,073 | 2,584 | 2,535 | 1,799 |
| (2,3) / 2.5 | 4,073 | 2,655 | 2,535 | 1,829 |
| 3 | 4,073 | 2,655 | 2,535 | 1,829 |
| (3,4) / 3.5 | 4,073 | 2,655 | 2,535 | 1,829 |
| 4 | 4,073 | 2,655 | 2,535 | 1,829 |
| (4,8) / 6 | 4,073 | 2,655 | 2,535 | 1,829 |

The lowest measured errors occur in different regions: ABA D1 at B<1, D2
at B<.5; ABC D1 at 1<B<2, D2 at .5<B<1. Those are comparisons within each
declared reachable-position distribution, not a causal population effect of
composition independent of reachability. The count-matched witnesses above
separately establish a concrete mechanism. The learned ABC coefficients,
which also change C, beat every measured B-only setting at both depths here;
this is not a proof over an arbitrary continuous price domain or unfamiliar rules.

## Fitting WDL is a distinct supervised control

For each current-player material vector x=(a,b,c), the observer uses proven
WIN/DRAW/LOSS targets y=1/.5/0 and fits only r in [0,8], A=C=1:
`p=(1+tanh((a+b*r+c)/10))/2`. This is oracle-supervised BCE, not TD experience,
an exact WDL probability, or a proposed intrinsic material table.
Convex derivative bisection gives r=.2742423082 in ABA and .6426666589 in ABC.
Those values do not select a single universal decision optimum, as the public
table already demonstrates. At link scales 1/10/100, the same ABC histogram
instead fits r=.2542421360/.6426666589/4.5534533835. The link and its absolute
scale matter; changing the statistical objective changes the fitted ratio.

The complete oriented-material histograms also give a representation limit.
Even an arbitrary three-class function of the **full material vector** must
misclassify at least 9,480/6,690 ongoing ABA/ABC Positions, because identical
vectors have different exact WDL. This is a WDL classification bound, not a
bound on search decision error. Geometry and history can resolve distinctions
that a material-only position predictor cannot represent.

One analysis-only numerical error was caught before publication. The hand-written
expression `a+b*r+c` can differ by one ULP from this Python version's compensated
builtin `sum`, used by Model.raw. The original ABC TD-projection-only table
therefore falsely split some ties. Its D1 forced-error/unsafe-tie pair
1,281/2,638 corrects to 1,219/2,700; D2 791/1,771 corrects to 761/1,803.
The observer now calls Model.raw. All public queries already used Model.raw;
the learner and shared search needed no numerical change. The dyadic B-axis
representatives are unaffected. Original outputs and the explicit correction
remain evidence; this does not rewrite a historical experiment.

Six exact leaf-equality lines through A=B=C=1 partition a small B/C neighborhood
into twelve open chambers. Twelve representatives are chosen algebraically,
without WDL selection. Their complete public D1/D2 comparison adds 812,616
queries in 644.30 seconds under its 1,200-second allowance: zero missing/UNKNOWN,
and every action independently agrees with its literal Model.raw minimax set.
No training is added and no representative becomes a default.

| B | C | D1 errors | D2 errors |
|---:|---:|---:|---:|
| 1.03 | 1.01 | 2,685 | 1,883 |
| 1.03 | 1.02 | 2,685 | 1,886 |
| 1.02 | 1.03 | 2,816 | 2,076 |
| 1.01 | 1.03 | 2,816 | 2,071 |
| .99 | 1.02 | 2,732 | 1,894 |
| .98 | 1.01 | 2,732 | 1,882 |
| .97 | .99 | 2,403 | 1,522 |
| .97 | .98 | 2,403 | 1,521 |
| .98 | .97 | 2,271 | 1,324 |
| .99 | .97 | 2,271 | 1,326 |
| 1.01 | .98 | 2,361 | 1,527 |
| 1.02 | .99 | 2,361 | 1,532 |

The learned chamber contains (.99,.97). Its representative has identical
67,718 public actions AND node counts to the trained endpoint. The adjacent
(.98,.97) chamber changes 49 D2 actions and 74 node counts, fixes two errors
without a WDL regression, and has identical D1 choices. Learning enters one
of the two most useful measured chambers; it neither identifies a unique
coefficient vector nor reaches the strictly best D2 representative in this
finite census. Arbitrary perturbation is not uniformly beneficial either.

The closed RNG run briefly enters the adjacent chamber after episode 2, then
returns after episode 3. That update changes B by +.000652618 and C by
-.003771631, entirely from nonterminal bootstrap terms; terminal-PV and final
outcome contributions are zero. The margin 2B-(1+C) crosses from -.001467242
to +.003609625. Four actual frozen-pre/post D2 calls at the two selected fresh
counterexamples (indices19468/20954) verify DRAW-valued choices becoming LOSS.
These are selected counterfactual states, not necessarily experienced states.
At the same episode's twelve actual learner histories, reuse the original
before searches and query only the after model: one action changes but zero
WDL qualities improve or worsen. Thus this bootstrap update has no measured
immediate quality gain on those histories while admitting the two fresh-state
regressions. This is a local mechanism, not a claim that TD generally fails.

The next executable check has begun: two simple original-root Core paths reach
those selected Positions in 20/21 plies and replay legally with full history.
Their actual-history WDL and pre/post decisions remain **NOT COMPUTED**. The
fresh labels above must not be silently assigned to those played histories.

## What the closed learning trajectories actually changed

The D2-foe endpoint is `[1,.9900874213,.9659358144,1,1,1]`; the RNG-foe endpoint
is `[1,.9759343935,.9344513766,1,1,1]`. There is no new training in this study.

Across all 27 ABC material vectors, compare all 351 pairs of literal leaf scores.
The D2-foe run changes region only in its first update: all 32 after-episode
models lie in one region, despite 14 weight-changing updates. The first-update
model and final endpoint are then checked with actual public search at every
ABC observer Position: **67,718/67,718 actions, node counts and WDL labels are
identical**, all requested D1/D2 complete, 514,367 new nodes, 60.25 seconds under
the unchanged 180-second cap. The RNG run visits three after-update regions
and changes region four times, but finishes in that same D2-foe region.

An order-preserving mapping of a finite set of leaf scores commutes with
min/max. Thus identical complete leaf ordering implies identical ideal
finite-depth q0 optimal-action sets in this 27-vector world, with terminal
scores/distances preserved. It does not prove unique prices, equal bounded
runtime, identical selected ties in arbitrary implementations, or equivalence
after adding inventories/features outside that set. The public comparison
above measures the selected ties and nodes in its stated scope.

Frozen-path TD decomposition reconstructs all updates to at most 1.2e-16.
In D2-foe training, total B/C changes split into nonterminal-bootstrap
(-.0065456,-.0113477) and terminal-PV-target (-.0033670,-.0227165) contributions;
the final actual-outcome residual contributes zero. This does **not** mean
terminal information was absent: search PV draw targets already enter interior
TD transitions. RNG-foe training has nonzero final residual contribution
(-.000401859,0) and one actually verified player-0-winning PV among 31 terminal
PVs. In that episode the learner is player 1, so this predicts the learner's
loss, not its win. The RNG opponent declines the immediate mating PV while
initially retaining a forced win, then discards that win at actual ply 10;
the game eventually draws. Search value and actual weak-opponent outcome are
different observations; this is not a falsely observed learner victory.

## Exploration coverage and older evidence

Zero-new-search replay of the closed RNG-foe run finds 557 distinct complete
histories / 429 Positions, versus 102 / 94 with the D2 foe. Of 324 learner
choices, 33 have different exact WDL among legal actions, and 18 incur regret:
13 discard a win for a draw, five turn a draw into a loss. The RNG foe has
16 regrets in 325 actual replies. There are 518 newly visited histories and
360 newly visited Positions relative to the D2-foe records, including
266/191 at learner choices. Greater coverage and larger drift did not produce
a different final material-order region. These correlated, fixed-opening
records are not independent strength samples.

The 85 preselected common C-only horizontal/vertical actual histories also
complete all 1,020 frozen-model D1/D2 slots: three identical prior root queries
reused, 10,967 new nodes, 6.89 seconds, zero missing/UNKNOWN. Nineteen exact
history values change, but uniform and closed TD have identical error counts:
horizontal 2/0/0 and vertical 1/1/1. Several actions and costs change without a
quality gain. History labels are computed from the full legal prefixes; they
are not substituted with the fresh-position census labels.

Task2620 receives only a zero-search examination of the already-selected
TDLeaf/initial first-divergence cap mismatch, slots 206/207, relative ply 137.
Equal earlier actions cost 14,483/14,515 nodes, leaving requests 5,517/5,485.
The returned complete queries spend only 69/71 nodes and about .0067 seconds
against 2-second caps. Request inequality alone cannot explain this first
promotion choice, g2g1r versus g2g1n. TDLeaf later checkmates; initial eventually
has an incomplete 13-node request at its original 20,000-node slot cap.
Preserve that UNKNOWN and all six original panel bounds. There is no rerun,
sample refill, reclassified draw or post-selected causal population.

## Cost, failures and reproducibility

The observer graph analysis closes in 345.87 seconds under its original
900-second deadline, including recovery. A fractional cell name initially used
`/` as a path component after all ABA labels were complete; those labels were
reused, the filename fixed and stop-file reads throttled to .2 seconds. Original
source/failure and the original deadline remain. Root-blocked label generation,
algebraic action sets and actual public search have distinct costs.

Generated query logs, graph caches and source snapshots stay under ignored
`artifacts/`; only this report, compact scientific evidence, reusable analysis
code and meaningful regressions are delivered. Run the existing graph
constructors in `scripts/leaper_retrograde.py`; `scripts/leaper_parameter_regions.py`
contains the observer analysis/public caller. Caches are own generated pickle
objects, never third-party inputs. The full graph query contracts, compact row
shapes and frozen model definitions are saved with each run.
Full learning/PV trajectories remain local; their reconstruction checks were
executed locally. The curated evidence supplies scientific inputs, aggregates
and selected Core certificates, not an independently remotely replayable archive
of every query or learning trajectory.

147 related tests pass, covering Core/history attractors, the rank shortcut,
graph versus actual Core D1/D2 arithmetic, independently compiled fresh-game
observers, public learner/search, incremental runtime/learning and TDLeaf.
Old stops, caps, UNKNOWN, closed models/failures and the ACTIVE 90-minute
heartbeat are retained. No new worker, Agent, Goal or scheduler is created.
