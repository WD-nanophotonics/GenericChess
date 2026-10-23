# Leaper strategy certificates, forward width and finite cost — 2026-10-24

## Decision and scope

The exact rule7 opening is now WIN for side0 with a supplied all-defense mate bound of7. The previous3->7 example still destroys one winning King action, but both roots are WIN. It is an action/strategy change, not a root-value regression. The old E0/E1/1920-slot experiments remain closed and their1904 missing outcomes remain UNKNOWN.

For the scoped singleton case, root branching is orbit-additive and forward two-ply history width is an exact quadratic with nonpositive pair interactions. This is an interpretable structural coordinate, not a price or generic difficulty scalar. A new two-ordinary-actor control has a nonzero third finite difference and refutes extending that quadratic law by ignoring quantity.

The finite Native cost screen keeps positive, negative and censored results separate. Actual paid work, completion of a requested iteration, terminal shortcuts, query latency and total recording cost are different targets. No Player/default, sampler, learner, full-history solver or AUX checkout is changed.

## Closing the actual strategy gap

Chat reply1792775120 supplied mathematical reasoning, not executed Core evidence or an independent engine. PRIMARY replayed the supplied strategy against **every** legal defender child, retaining full records, repetition counts and H64/repeat4 clocks. There are22 nodes and5 checkmate leaves, at absolute plies5,7,7,7,7. No shortest-distance assertion is made.

The missing ply2 position has K0=(0,0), A=(0,1), K1=(2,0). The supplied attacker choices are A to(1,2), K0 to(1,1), then A to(2,1). Both defender branches are checked. Together with the original PV and two earlier one-ply closures this supplies the complete root certificate. The typed GameRecord/Action serialization boundary initially failed; formal deserialization fixed the caller without changing any scientific expectation. Omitted off-PV policy, PV-only policy, a falsely shorter bound and a renamed fingerprint are rejected.

The independent static-capacity proof review supports the prior active-offset iff criterion only within its stated single-Leap/King8/square/no-extra-effects scope. The reply's obsolete Dot budget-review instruction is rejected in favor of current user policy.

## Fixed metadata strata and event laws

Before the new finite forward check,24 one-bit edges were selected by a deterministic metadata hash:8 component-changing,8 parity-only,8 stable edges, classified using4x4 empty graphs. The population stratum sizes are18/9/48. The same stratum labels are carried to5x5/6x6, not recomputed after observing results. Some edges and4/5-board properties were already exposed controls;6x6 is a separately new board envelope. These are not blind WDL holdouts.

All31 masks use the same8 physical fresh roots per board, selected by a coordinate hash before calls. The744 complete roots have7560 literal one-ply Core edges matching a separate scoped integer calculation. The576 paired contrasts have76 newly available immediate mating actions. Width decreases90times, increases445times and stays equal41times. All90 decrease cases are checked through complete Core two-ply frontiers:154 unique roots,1449 first edges and3799 second edges. Forty-four decreases have no first-ply terminal, so absorption is not their only mechanism.

An existing immediate mating action cannot cease mating merely by adding a disjoint ordinary movement/attack orbit in this exact singleton-versus-bareKing scope: its own legality is preserved, the victim stays checked and defender escapes only disappear. This does not order eventual minimax action values or uniform-action probabilities. A targeted diagnostic finds mask5->7 at K0flat1,Aflat15,K1flat3: the same sole A15->11 mate exists in both, but total legal moves change7->8. The immediate uniform-action mate probability falls1/7->1/8. This diagnostic is a counterexample search, not a new population estimate.

## Why two layers are quadratic, and where that stops

For a fixed shared fresh position, every outer ordinary action needs one orbit bit x_i. A bare-K defender destination can be attacked by at most one of the five disjoint offset orbits, giving a factor(1-x_j). Capturing A removes its attacks; royal protection and occupancy are fixed geometric conditions. King outer actions have no x_i gate. Summing these terms and reducing x_i squared to x_i gives

W2(x)=c0+sum_i c_i*x_i+sum_(i<j) c_ij*x_i*x_j, with c_ij<=0.

Thus the marginal width contribution of an added bit decreases as other bits are added, although it can be negative. The formula matches all744 profiles. Exact rational mean coefficients are derived over the full geometric common supports596/4712/20340 on4/5/6 boards. Validation compares all18476 integer profiles on4x4 and496 each on5/6; the latter full support census is coefficient derivation, not an assertion that all those roots/trees were rerun through Core.

The next boundary check is actually executed: on5x5 put K0flat0,Aflat11,Aflat7,K1flat24, both ordinary pieces sharing the variable type. All31 nonempty masks are compiled and their literal Core depth2 trees give839 second edges. At base mask4 and varied bits0,1,3 the widths for masks4,5,6,7,12,13,14,15 are23,43,35,51,30,34,36,40. Their third difference is4, so no quadratic extension represents this input. It is not a WDL, quantity-price conservation or all-DSL theorem.

The mean widths for masks1/5/31 are respectively2466/149,2650/149,1738/149 on4x4;18293/589,42527/1178,22259/589 on5x5;71021/1695,258289/5085,112199/1695 on6x6. Each board has its own declared common mu; these are not one-factor board causal effects.

## Registered cost screen

There are24 previously cost-unmeasured masks (the earlier7-mask cost casebook is excluded),3 boards and8 fixed roots:576 contexts. Each gets a fresh Player/TT under explicit unit A1000/King0 leaves with dynamic bonuses off, Q0/forced-check8, requested depth64, Native service variant all, and a3second cooperative clock. Node caps32768/131072 are an explicit curve. Each budget is one process, not a fresh process per query. Startup/provider caches and concurrent load remain limitations.

The forecast allowed3456 cooperative query-seconds plus preparation/recording/analysis, expected90minutes total below120; batch caps1900seconds and total4000seconds are frozen. Missing slots are never refilled. The original primary comparison is Spearman with ties, reported at both root and rule-mean level and separately by board/budget. It compares graph components/degree, root branch and two-ply width with actually paid nodes+qnodes, observed completion depth and latency. It does not infer latent work needed to solve the game or requested-depth completion from a time-censored return.

|Board|Node cap|Calls|Root wins|Node limit|Time limit|Mean counted work|Median completed depth|
|---|---:|---:|---:|---:|---:|---:|---:|
|4x4|32768|192|41|0|151|16541.40|8|
|4x4|131072|192|41|0|151|16312.04|8|
|5x5|32768|192|14|3|175|23107.18|7|
|5x5|131072|192|14|0|178|22781.06|7|
|6x6|32768|192|10|3|179|25350.75|6|
|6x6|131072|192|10|0|182|24964.11|6|

All1,152 planned queries are retained;0missing. There are1,016 time-limited returns,130 literal root wins and6 node-limited returns. All6,818 PV plies and chosen actions replay through Core. Native providers are available for all1,152 returns, with0 recorded legality fallbacks. This does not establish an independent engine or uncensored completion cost.

|Board|Node cap|Width vs counted work rho|Components vs counted work rho|
|---|---:|---:|---:|
|4x4|32768|0.919862|-0.128788|
|4x4|131072|0.932493|-0.126335|
|5x5|32768|0.468131|-0.478357|
|5x5|131072|0.479878|-0.482036|
|6x6|32768|0.324348|-0.448919|
|6x6|131072|0.355652|-0.451372|

The first budget's total-work rule-mean correlations with width versus component count are respectively0.9199 vs-0.1288,0.4681 vs-0.4784,0.3243 vs-0.4489 on4/5/6. The original prose did not freeze signed versus absolute correlation as a formal winning criterion. All signed values are delivered, with no posthoc acceptance test: under the absolute-association reading, width is strongest on4x4 total work but does not reliably dominate components on larger boards. Empty-graph degree correlates more strongly with observed completed depth than width on these cases. All original targets are retained; the favorable4x4 association is not substituted for the full screen.

The32768 batch spends1532.85seconds inside queries,2.79 in Player setup and3.82 in rule setup out of1809.40seconds. The269.93second outer residual includes recording, replay and other controller work. A zero-Player diagnostic on32 explicitly derived prefix packets measures4.31seconds in the existing atomic writer,1.76 in conversion and2.16 in direct JSON dumping; direct dumps have identical bytes for these already primitive packets. These are not historical original snapshots or a measured whole-run speedup. No serializer bypass or running-caller change is installed. Inner nested search timers are not summed as disjoint costs.

## Delivery, interpretation and next step

The compact bundle preserves exact scientific JSON/text originals, complete rules/records, actual query returns and data-only executed-source capsules. Its reader restores scientific data only and never executes source capsules. It verifies copied inputs, all retained PV actions, all finite one-ply/decline frontiers and the certificate. The full mean coefficient census is retained producer evidence with explicit validation coverage, not a claimed independent engine rerun.

The next independent check is whether the symbolic singleton decomposition misses any rule assumption; the two-actor failure is already a concrete boundary. Continue interpreting the saved cost counters and terminal-shortcut mixture before buying another query panel. Full generated promotion/drop/auxiliary/history semantics remain the long-term target. No root/depth/clock/representation coordinate alone selects quality, utility or a universal learner.

Direct review: [finite mate7 certificate](data/leaper_forward_width_20261024/mate7-certificate.json), [quantity/probability boundary inputs](data/leaper_forward_width_20261024/boundary-and-probability.json), [full cost summary](data/leaper_forward_width_20261024/screen-summary.json), [exact evidence and reader](data/leaper_forward_width_20261024/README.md).
