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

Raw total and raw capture opportunity have the same64pair signs here. Moving
from those default-law values to actual projected counts changes some signs;
count-to-any changes further signs. Any-to-legal-task changes none of the64
aggregate signs, although numerical means differ. Merely listing quiet/capture
components will not fix these observed inversions. These stages change multiple
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

## Recovery and next decision

[data/qfrontier_20261009.json](data/qfrontier_20261009.json) routes producers,
original failures, complete records, exact arithmetic and source/input pins to
the purpose-specific archive. Original/private and redacted/public hashes are
separate; a redacted declaration is not byte-identical original evidence.

Keep current defaults. Next research should select one task whose fixed-choice
headroom is genuinely decision-changing, or one observed generic interface
failure, rather than add more uninformative horizons or infer new prices from
these sparse exposed checks. No new framework, NNUE, Elo target or deployment
gate is established.
