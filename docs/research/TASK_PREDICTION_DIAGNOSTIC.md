# Fixed rule-only prices as task predictors

2026-10-09. Exposed development evidence, not a new material table or strength
claim. The useful result is narrower than "static prices work": frozen top
choices outperform a uniform blind choice on one immediate task in eight
existing rules, while complete ordering, temporal transfer and reply support
have concrete failures. Generic-v2 and semantic-v3 have identical rankings in
this cohort; none of these results establishes a v3 improvement.

## Population, reward and comparison

Reuse the four existing6x6 routes (seeds202610082000..2003) and four existing8x8
routes (202610082100..2103), initial position through16existing route plies.
Every actual ordinary side-to-move slot is replaced counterfactually with each
ordinary type:614slots/four types and886slots/five types. This is a diagnostic
intervention, not a claim that a legal game can replace one piece with another.
No new seed, route, PV-based selection, human-label fitting or holdout claim.

Immediate reward is the maximum legal focal-action removal of ordinary enemy
board-plus-hand units, with a virtual stop worth0. Anchor wins, history-based
adjudication and future service are outside this reward. One-reply reward uses
the same previously declared short-exchange definition: immediate removal minus
the worst legal opponent ordinary removal, again maximized with virtual stop0.
Legal action generation is real Core execution. Rewards never use price scores.

The law is equal slots within each background, then equal17backgrounds per rule.
Missing complete slots are reported, never filled with0; none are missing here.
Static price ties split uniformly. Loss is slot-oracle reward minus selected
reward. The blind comparator selects uniformly among all ordinary types.
Negative loss-minus-blind below means useful selection on this declared task.

|Seed suffix|Frozen top|Immediate loss minus blind|One-reply loss minus blind|Reply all-zero slots|
|---|---|---:|---:|---:|
|2000|P|-40433/942480|-223/58905|134/145|
|2001|B|-355961/1884960|-237/9520|142/149|
|2002|A|-1051/7480|-1/85|144/175|
|2003|A|-268571/1884960|-1321/28560|137/145|
|2100|A|-1321/60060|0|224/224|
|2101|A|-1282459/6126120|-29/2340|185/195|
|2102|X|-347/30940|-59/4420|236/245|
|2103|P|-18631/77350|-4/1105|221/222|

Immediate complete-type choice helps8/8rules. One-reply choice helps7/8, with
one entirely uninformative rule. The8x8immediate extension completes4430cells
and12244focal Core/Native transition parity checks. The6x6immediate record is
reused intact. Reply computation completes73592/125792Core transitions and
68/64selected full-reply-set parity controls (2829/4376Native transitions).
These controls qualify execution, not independent statistical validation.
Nonpositive-gain reply expansions are exactly dominated by virtual stop0 and
skipped with recorded bounds. Declared per-rule120second/100000Core-transition
cost checkpoints are respected; no original search cap was extended.

## Ordering and information ceilings

All64pair comparisons are retained: four rules with6pairs, four with10pairs.
Mean pair loss is worse than blind in3/8immediate rules despite useful top choice.
The original B/X check alone fails on2003. Best observed constant type, best
background-specific type and best slot-specific type are descriptive information
ceilings using observed labels, never deployable fitted predictions.

|Seed suffix|Immediate fixed-choice headroom|Reply fixed-choice headroom|Reply unavoidable fixed-choice loss|
|---|---:|---:|---:|
|2000|1/170|21/935|19/765|
|2001|0|0|1/85|
|2002|7/110|12/187|52/935|
|2003|0|0|0|
|2100|165481/1021020|0|0|
|2101|0|0|365/15912|
|2102|379/18564|0|1/102|
|2103|0|0|0|

Headroom is current fixed-choice loss minus the best always-one-type loss.
Unavoidable fixed-choice loss is best constant loss relative to the slot oracle.
Thus this immediate metric leaves fixed-choice improvement in4/8rules; the
reply metric leaves it only in2000/2002. A conditional reversal alone does not
prove a static generator needs repair or a position model is necessary. A large
conditional ceiling does not prove a small network can learn it. No inferred
ordering validates full price ratios, deployment or universal material utility.

A further complete-ranking audit enumerates1152strict orders across the two
tasks/eight rules. Sorting observed task means attains the simultaneous minimum
mean pair loss, checked against all24/120orders per rule. Fixed-ranking headroom
remains7/8immediate and6/8reply rules, even when top-choice headroom is0.
Therefore a saturated top-choice metric cannot close the ordering research line.
These observed-label best orders remain descriptive ceilings, never fitted
prices or generalization evidence; allzero2100reply remains uninformative.

Correction after analytical cross-check: raw total and raw capture opportunity
agree on62/64pair signs. The exceptions are2100C/X and2101P/X; the earlier
published64/64summary was incorrect, while its original component data were
intact. Capture-only changes those two choices in the favorable direction on
this exposed task; it is not equivalent to the unchanged total-opportunity
predictor. Moving
from those default-law values to actual projected counts changes some signs;
count-to-any changes further signs. Any-to-legal-task changes none of the64
aggregate signs, although numerical means differ. Merely listing quiet/capture
components does not remove all observed inversions. These stages change multiple
conditions and are not isolated causal effects.

One non-fitted changed-premise probe tests saturation alone under the SAME
default density law and uniform owner/source average. It computes probability
of any supported projected capture rather than expected count, using two fixed
RNG replicates of128full layouts per density, shared across all types. Both
replicates give the same orders: immediate mean pair loss improves only2000
(-9017/706860), worsens2100(+34381/1458600), and is unchanged in six rules.
No favorable replicate or new coefficient is selected.18exact three-color
enumeration/closed-form ray, leap and cannon controls pass; maximum observed
sample count error against the exact existing curve is0.03752. This is a finite
approximation, not a confidence interval or semantic-equivalence guarantee.
Default-law saturation alone is therefore not a useful general replacement on
this cohort. Context/source bias remains a specific unresolved mechanism, not
permission to tune exposed labels or replace product prices.

A matched2x2continuation separates uniform versus initial ordinary-slot source
weights and count versus any-capture on identical layouts. Template-source any
improves5/8immediate pair losses and leaves3unchanged in both replicates. The
analytical endpoint-count control finds one sampled ordering discrepancy: the
second2101template-count replicate reverses B/C. Uniform-count orders agree
with the analytical control; their differences from current prices in2100/2101
are the real raw-total/capture exceptions above, not sampling errors. The
earlier local checkpoint's uniform-error attribution was corrected explicitly.
Both replicates agreeing is still no exact-any probability guarantee. This is an
adaptive source-law diagnostic; old template/rare-bridge counterexamples stand,
and no new source distribution, price or default is adopted. Probability checks
can diagnose a candidate; exactness is not a prerequisite for scoped development.
Temporal transfer matters to deployment claims, and exposed whole-route
improvement alone does not establish them.

The original early/late and owner partitions were then applied without changing
these frozen template-any orders. All eight rules/two replicates retain
nonpositive mean full-pair loss changes in every such stratum; the5improved/
3unchanged whole-route means reproduce exactly. This rules out one simple
phase-aggregation explanation for this adaptive signal, not unseen-rule
generalization, exact probability or universal context choice. Individual
background changes remain in the full audit rather than being filtered away.

A final source-local exact feasibility check takes the first ordinary template
source of each owner for2100C/X and2101P/X. All8cases have1..7distinct projected
endpoint events. Rational colored-event inclusion/exclusion completes within
the12event boundary and passes18closed-form elementary controls. This does not
yet average all sources or confirm the Monte Carlo ranking. It makes one
bounded exact next check executable without a new framework or product change.

## Sparse and counterfactual support

Reply rewards leave557/614 and866/886slots allzero. Seed2103's apparent reply
advantage comes from one positive cell. Predeclared early/late and owner strata
show harms hidden by whole-route means; leave-one-background influence can
reverse seed2000's reply advantage. These are finite sensitivity ranges, not
confidence intervals from independent samples. Primary weights remain unchanged.

Actual replay audits every positive reply action. Seed2002 has31positiveactions,
all checking the opposing anchor;27have no legal reply, and4start with that
anchor already checked after counterfactual replacement. Its P>B/X reply
inversion is mostly check/evasion structure, not broad safe material retention.
By contrast2101has20positiveactions, none checking;2102has24, four checking.
Keep all original cells, including no-reply cases, rather than repair the result
by excluding an inconvenient stratum. This audit explains scope; it does not
convert the reward into WDL or certify reachable counterfactual positions.

## Search and custody controls

At the old seed102D3PV leaves, independent finite-q replay explains the local
3507/2552root-score discrepancy: q0's selected third move falls to2234 after
recapture, while the q2 branch reaches2552 with a318promotion contribution.
All31legal third actions were checked under matched unit/v3q2 conditions.
This local frontier is not a root minimax certificate or stronger-player proof.
The original failed action parser is retained alongside the corrected producer.

A changed mixed-hand premise gives two capturable current-R victims with P/Q
bases and only Q having live drops. Mirroring assignments changes actual hand
stock; D1old/P-zero supplied leaf choices differ and Q's subsequent drop is
available only after the Q capture. All8D1/D2calls match full-width references.
D2both leaf variants choose the same escape instead, so no deeper gain or
broader zero-hand classifier follows. Keys, default profiles and product code
are unchanged by this segment.

## Primary-source checks and decisions

[Pav, *Inferring Piece Value in Chess and Chess Variants*](https://arxiv.org/html/2509.04691)
warns about policy, skill and sampled-position confounding; its self-play
ablation still depends on evaluator and sample selection. Adopt that warning,
without importing human prices, datasets or fitted coefficients. Our task
rewards are independent of the score, but exposed route selection remains a
limitation; reward independence is not validation independence.

[Feys, *The Arithmetic of Chess Piece Strength on the nÃ—n Board*](https://arxiv.org/html/2605.20229)
explicitly studies geometry rather than practical material value and uses a
single-color Bishop convention. Local actual-target enumeration for n=4..12
matches ordinary B total2n(n-1)(2n-1)/3. Halving that is not the ordinary B mean:
at8x8the conditional mean on either color is8.75, while280/64=4.375. On5x5the
two color totals64/56 are neither the half-total60. Adopt an explicit convention
adapter; do not import the paper's half-B/King ratio as ordinary engine capability.

[Muller's firsthand discussion](https://www.chess.com/forum/view/chess-variants/help-why-dont-fairy-chess-pieces-have-values?page=4)
describes army-substitution tests and empirical occupancy/source assumptions.
This supports treating context and policy as declared assumptions; its fitted
weights and source optimization are not rule-only universal constants for us.
No replacement coefficient is selected from these sources or our exposed data.

Dot's two complete replies were read and reconciled. Adopt its sample-selection
objection and one best-fixed-choice ceiling analysis; defer expanding the
single2002inversion into a new task family. Dot read the published base and our
reported new evidence; it did not execute these local experiments. Raw Slack
records remain local and excluded from Git.

## Crossed population diagnosis and prospective source-prior check

The2104B/C discrepancy is now examined with crossed factors, rather than a
single count-to-legality conversion chain. Use the original independent-density
law and uniform owner/source positions versus all frozen actual ordinary slots;
compare supported projected ordinary capture-endpoint count and capture-any
under each. Both128-layout replicates favor C for uniform count/any and B for
actual-slot count/any. Actual ordinary B-minus-C contrasts are298013/510510
for count,66961/437580for any and63001/437580for legal maximum removal. The
first diagnostic included actual anchor endpoints; its output is retained as
superseded support evidence, not the comparable ordinary-unit result.

Separating source weights from occupancy preserves an interaction: on identical
IID layouts, route-slot source weights alone reverse both signs; actual occupancy
alone also reverses them. Analytical capture-count B-minus-C is-0.296870under
uniform sources,+0.313037under frozen route-source weights and+0.372240under
initial ordinary-source weights. Quiet/total components also reverse. This
does not identify a unique cause or a uniquely rule-given background law.
2105retains the opposite source effects. No statistic or label is fitted.

All5855legal focal transitions have ordinary-removal gain0or1, so legal-any
equals legal-max on these2210cells. The projected any differs in49cells of2104,
including26B/Ccells, and zero cells of2105. B/Craw S0-S2 candidate endpoint
counts exactly match projection; complete legality changes support without
causing the aggregate sign reversal. This equivalence is measured here, not
assumed for compound effects in the full rule domain.

The unchanged one-reply task completes all2210cells in56859Core transitions,
with23complete reply-set/child-state Native controls totaling1709transitions.
2104static C loss is20408/255255, worse than blind by995/68068; the frozen2048
B selector has zero loss. However179/196slots are zero and all20positive actions
give check, four with no legal reply, none already checking before the move.
This is check/evasion support, not broad safe-retention evidence.2105has241/246
zero slots and nine nonchecking positive actions; all selectors keep X.

Two existing2104successors give a concrete omitted-utility witness: the legal
quiet X-to-P transformation at ply7 and semantic drop at ply11 both have zero
enemy ordinary-removal reward while changing full state/current identity,
hands or auxiliary state. Session and Core child identities agree. A zero proxy
reward does not establish zero utility for either mechanism.

A changed initial-source prior is then frozen on four *new* rules2106..2109
before any task labels: shared equal initial ordinary slots/both owners,
unchanged IID densities, analytical capture-count or total quiet+capture.
Both candidates and all previous static/learned tables are frozen on all four
rules before the first query. No seed replacement, refit or model selection.
All68backgrounds/899slots/4495type cells complete, with14554full Core/Native
transition matches. Whole task weights, all zeros and excluded semantic effects
remain explicit. Prior rare-bridge/source-law failures are not revoked.

|Rule|Static immediate top loss|Both source-prior top losses|Immediate pair change|One-reply top change|
|---|---|---|---|---|
|2106|474599/1021020|643/18564|both improve|both improve|
|2107|1355821/1531530|17227/48620|both improve, different orders|all zero/tie|
|2108|3581/7140|23/364|both improve|both improve|
|2109|1741/18564|1741/18564|both worsen|both tie|

All four one-reply populations complete in166929Core transitions. Pair loss
improves2106/2108, ties all-zero2107, but worsens2109despite its top-choice tie.
Positive support is44/0/2/7cells;2106has21checking and29nonchecking positive
actions, three already checking before the counterfactual move; the other new
rules' positive actions are nonchecking. No favorable support filter is used.
Top-choice gains therefore do not establish a better full ordering or ratios.

Offline candidate-pair preparation is0.039-0.074seconds in four local calls,
versus0.056-0.080for the old v3 profile, excluding compilation. All frozen
tables reproduce. The same mechanism keeps Chess Q>R>B>N>P but changes its
raw opportunity ratios; Shogi initial-source total puts R above TB and L above
S while capture does not. These are declared opportunity-law differences,
not material truth or human-price fitting; Xiangqi holdout remains closed.

Retain the changed-prior candidate as a scoped comparator, not a default or
universal price. A fixed-ordering leaf caller comparison separately tests whether
its normalized board table crosses the full generic search-state interface;
hand prices and ordering authority stay fixed. Changed choices are sensitivity.
Exact one-reply pair decomposition places the2106 improvement entirely in C/P,
the2108 improvement in A/P, and2109's worsening entirely in B/C:43/3315 on
that pair,43/33150 averaged over ten pairs. The unchanged2109 top choice hides
this adverse middle ordering.2107's one-reply cells are all zero.

Actual leaf-only callers use all68 frozen route roots, three tables and q0/q2,
408 cold Core calls with fixed unit ordering and shared old hand prices.
D3/2048nodes/2seconds completes22/68,23/68,22/68 for q0 static/capture/total;
q2 completes1/68 in each arm. Total query times are104.95/104.15/104.04seconds
for q0 and134.66/134.24/134.57 for q2. Every PV replays legally and roots stay
unchanged. These caps and choice changes are execution/sensitivity, not gains.
All eight source tables preserve their ten raw ordinary pair orderings after
normalization, with no clipping. Keeping hand prices fixed intentionally changes
board/hand ratios: this isolates board leaf prices, not a consistent joint
material proposal. A separate whole-root short-task diagnostic retains unknown
references rather than interpreting cap failures as zero:22/68root references
complete in528.33seconds, with46UNKNOWNs and zero optimal net in all22completed
roots. This proxy's virtual-stop oracle need not be a legal forced move.

A separate cheaper question evaluates only the union of actual selected actions
from all six arms, reusing already complete action references and keeping the
original oracle caps intact.5997extra transitions/59.97seconds cover all68roots.
The capture candidate improves two q0 and three q2 choices on2108 but worsens
one q0 choice on2109; other paired net outcomes tie. The total candidate ties
everywhere. q2 improvements still have incomplete D3 searches. These are
ordinary-removal net diagnostics on policy-dependent selected actions, not
full-oracle regret, terminal-win/future-service utility or strength. The much
larger counterfactual top-choice gains do not transfer directly to actual use.
Keep this cheaper decision target available; do not expand whole-front oracles
or refit the report cohort merely to obtain stronger-looking results.

Recovery for these new producers/raw outputs is the source-prior supplement
in data/qfrontier_20261009.json; old archives and frozen teachers stay unchanged.

## Recovery and next decision

[data/qfrontier_20261009.json](data/qfrontier_20261009.json) routes producers,
original failures, complete records, exact arithmetic and source/input pins to
the purpose-specific archive. Original/private and redacted/public hashes are
separate; a redacted declaration is not byte-identical original evidence.

Keep current defaults. The2026-10-09direction review prioritizes the comparative
evaluation-route assessment in EVALUATION_ROUTES.md; full-template precision is
optional when its alternatives change a concrete choice. Next research may select
one task whose fixed-choice
headroom is genuinely decision-changing, or one observed generic interface
failure, rather than add more uninformative horizons or infer new prices from
these sparse exposed checks. No new framework, NNUE, Elo target or deployment
gate is established.
