# Resource generation, opening controls and material leaf value — 2026-10-22

The current Static baseline remains. On twelve preferred generated rules, removing
only board/hand material from the leaf loses 22 of 24 actual node2048 games; one
rule reverses both seats. The new thinning prototype has no established advantage
over the existing optional opening-win preference. Neither result changes a
default, creates a generator API, demonstrates learning, or transfers AUX work.

## Registered scope and accounting

[The technical capsule](data/resource_generation_material_20261022/README.md)
retains **190 NEW physical trajectories, 7,448 NEW Player returns and 20,468 literal
PV edges**. Another **24 cold returns/99 PV edges** are separate from fitness.
There are 216 planned physical slots across the batches: 14 exact reuses and
12 invalid-initial-state slots account for the difference. No frozen cap is
extended, no missing slot is replaced, and raw UNKNOWN is never changed to draw.

All controls keep full canonical rules, CURRENT board types, BASE hand types,
promotion paths, declared future types, auxiliary fields and complete histories.
The production-generator subset includes real promotion/drop play; it does not
cover arbitrary custom DSL token effects. Its grid is 4/6/8 boards × classic/free
setups × bilateral/no symmetry. The toy leap families are a separate exposed
4×4 prototype. Related configurations and adaptive follow-ups are not independent
holdouts or population samples. Intervals below are finite completion bounds,
not statistical confidence intervals.

Ordinary q-depth is zero, hard check bound eight, disk cache OFF, per-actor TT
fresh at game start and retained within that game. N2048 uses maxdepth64/node2048;
D1 stops at depth1 under the same ceiling. Caller96 is separate from the unchanged
rule clock. Actual depths, sources, counted work and time remain in the data.

## 1. The prepared Unit control did not establish an advantage

Eight new Static self games and sixteen new Unit-versus-Static games give 32 role
frames. Both actors share the same three-method Static ordering adapter; only the
candidate leaf changes. All 24 games complete sampling, including four caller
UNKNOWN. Full Core replay and 4,676 PV edges pass.

The balanced Unit contest is **[-7/16, 1/16]**. The single-seat Static self mean
is -5/8; subtracting it from a two-seat candidate would manufacture the incorrect
positive range [3/16, 11/16]. Exact opposite-role self reuse gives balanced zero.
Worlds18/20 are structural negative controls: only absent C prices differ, no
rule creates C, and all three physical action histories match in each world.
Complete C entries remain present. This is a scoped argument, not a reachability
framework or evidence that prices generally do not matter.

## 2. Resource retention is a context, not a universal quality improvement

Twelve NEW parent configurations produce 48 full-roster N2048-versus-D1 games.
Only capture disposition changes between the two variants; original drop masks,
promotion rules, all other fields and physical initial states remain.

| Full roster | N2048 signed utility | Raw UNKNOWN |
|---|---:|---:|
| Capture to hand | [2/3, 3/4] | 1/24 |
| Remove captured pieces | [7/24, 7/8] | 7/24 |
| Resource minus removal | [-5/24, 11/24] | Retained above |

The preregistered 4×4 subgroup gives [1/8, 3/8]; 6×6 and 8×8 ranges cross zero.
World10 contains a settled negative resource contrast. No favorable subgroup
replaces the twelve-configuration comparison. Restricted mean length through
caller96 is 425/24 plies shorter with resources. This quantity is observed even
when the eventual outcome remains UNKNOWN; it is not completed-game duration.

Canonical one-per-type thinning keeps all anchors and future rules but exposes
initial anchor attacks in worlds0/1/9. Preserve those twelve failed slots and all
36 completed sparse trajectories. Their conditional valid domain and the full
planned-completion sensitivities are both recorded. Initial failure is not a
terminal game outcome. In the full cohort, actual history checks cover 100
promotion actions, 171 drops and 50 captures of promoted pieces. Resource token
counts are conserved in this declared movement-only subset; this is not a generic
price-conservation assumption for arbitrary creation/expiry effects.

An execution precondition incorrectly required default removal-mode hand prices
to be zero. It failed BEFORE any Player call. `profile.py` deliberately assigns
finite hand coefficients independently of capture disposition. These generated
removal games start without stock and cannot create it. Source/default comparison
resolved the contract; default fields were kept, no product assertion was weakened.

## 3. Legal layouts exist, but validity conditioning changes the proposal law

A bounded census checks **38,661 distinct retained-square masks** over all twelve
parents. The three canonical failures have legal fractions **1/8, 1/8, 1/32**;
removed blockers, rather than a proof of impossible quantities, explain them.
The exact rejected rules and attacking-ray witnesses remain in the capsule.

For M masks and V valid masks, p=V/M. Sixteen independent uniform proposals with
replacement succeed with s=1-(1-p)^16. Given parent and success, accepted valid
masks are uniform. Accepted parents are nevertheless weighted by their own s.
For this finite twelve-parent mixture the modeled acceptance is 0.93018, expected
proposal count 3.06135 and parent total-variation shift 0.05630. These are exact
finite-count consequences of a specified law, not a new population estimate.

A disjoint twelve-seed cohort then freezes that bounded legal-thinning law before
fitness. All twelve accept their first proposal in THIS cohort; no general
acceptance guarantee follows. Forty-eight NEW full/sparse resource games give:

| Proposal | N2048 versus D1 utility |
|---|---:|
| Full roster | 5/12 |
| Bounded legal thinning | [2/3, 1] |
| Thinning minus full | [1/4, 7/12] |

However, full worlds0/4/5/8/10 have exact opening wins in one ply. Excluding them
only as a descriptive diagnostic leaves thinning-minus-full **[-1/7, 2/7]**.
All twelve remain in the primary comparison and four sparse UNKNOWN remain.

The cheap existing `require_no_opening_win_in_one` preference is therefore tested
before adding an API. Same twelve seeds/configs, only that flag changes: seven
execution rules remain exactly equal and five are replaced. Fourteen full-source
frames are exact hash/initial-state/controller reuses; only **10 NEW games/219
NEW returns** execute, taking 46.96 runner seconds. The preferred utility is **5/6**,
and thinning minus preference is **[-1/6, 1/6]**. This establishes neither equality
nor extra thinning benefit. Keep the existing option and defer a new mechanism;
there is no automatic default activation. This compares generator laws, not an
isolated modification of the same game.

## 4. Material leaf information has a large scoped marginal effect

All twelve preferred rules enter a new 24-game contest, with both actors using
node2048/maxdepth64 and the same Static ordering adapter. **M0 zeroes every board
and hand material coefficient**, while keeping Static promotion gains, median,
ordering methods and dynamic weights2/5/3. Thus M0 still contains prior information;
it is not heuristic-free or fully price-free search. The 24 cold preflight calls
also verify 169 exact full-state/child material decompositions.

All 24 fitness games reach true checkmate. Static wins22, M0 wins2, giving
**M0 versus Static = -5/6** and **Static versus M0 = 5/6**. World1 reverses both
seats and is retained. Full Core history and **2,901 PV edges** pass. This supports
marginal board/hand leaf information in this finite shared-order contest; it does
not establish an optimal table, learning gain, generic superiority or a WDL oracle.

## 5. Offline prediction is a different question

A no-fit diagnostic reuses 256 already-public games and 13,805 root views. Fixed
logistic score temperatures1000/2000 are declared before measurement. Unknown
outcomes share one target across all roots of their game; paired squared-error
differences are affine in that target, so endpoint bounds are exact. Equal game
weighting is distinct from pretending roots are independent samples.

On the resource N2048/D1 source, Unit-minus-Static error is -0.002332 at1000 but
+0.002289 at2000. A ranking can flip without changing any price policy or game.
Fifty-nine exact full-GameState groups carry different known terminal labels under
different continuations; all eight direct resource openings demonstrate this by
swapping the N2048/D1 actors. This does not refute expected-outcome or TD learning
under a fixed policy mixture. It prevents treating these retrospective labels as
policy-independent WDL or evidence that an offline-fit improvement changes play.

[Isaksen et al.](https://www.nealen.net/papers/08030128.pdf) model player-conditioned
survival distributions in minimal action games and explicitly limit transfer to
strategic difficulty. Here only descriptive terminal-cause/restricted-length curves
are used; no exponential fit or censor-to-draw conversion is introduced.
[Lantz et al.](https://cdn.aaai.org/ocs/ws/ws0340/15142-68464-1-PB.pdf) propose a
strategy ladder with resource and strategy-language assumptions, acknowledge
practical limits and discuss opponent/QM ambiguities. Our two controllers are not
proven resource-optimal strategies, so their observed contest is not a measured
universal depth or learning-capacity score. Neither source becomes an oracle gate.

## Delivery and next action

Run the public reader described in the capsule README. It reconstructs complete
histories/child states, checks all new literal PVs and reproduces required offline
scores from the fixed parent packet. Source is shared production Core: this is
independent reading of retained outputs, not an independently implemented engine.

The next question is already begun as immutable full inputs/profile tables and
actual AST24-slot checks: does the material-leaf result persist when BOTH actors
instead share Unit ordering? `next_*` has **zero Player calls and fitness NOT RUN**.
All twelve exposed rules remain; promotion dynamics stay fixed. A different
common ordering also changes the opponent, so the future result is a conditional
head-to-head robustness control, not the same fixed-opponent absolute effect.
No additional producer remains running after this segment.
