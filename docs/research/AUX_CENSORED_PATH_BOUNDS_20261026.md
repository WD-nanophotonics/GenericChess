# Censored Leaper paths: history-safe bounds and timing populations

Status: ENDED DEV_AUX session f34f609f, accepted safe_checkpoint finish at2026-10-26T15:37:36UTC with71.98539confirmed effective research minutes (4319.123103seconds). The preceding140a segment contributes no new credit.200relevant testsPASS plus3negative-source controls; exact intervals and uncredited interruption are in data/aux_censored_paths_20261026/session-finish.json. No new Player, solver, game, build, candidate, production setting or other-role work is launched. Token cost is UNKNOWN.

The same saved outcomes support several different descriptive targets. Keeping complete timed pairs gives exact experienced actor-regret difference2; retaining23timing-qualified individual games instead leaves an unknown initial potential and gives[1,3]. Their per-decision mean ordering is consequently not identified by these aggregate constraints. Filtering1930individual queries happens to preserve an exact mean difference2/965 because the omitted real move is forced and has regret0. These are consequences of one exposed source, not independent strength measurements.

## Sources and authority

PRIMARY data stay fixed at `fd7d7eacbdc2741e766f26b67b0f54018a998aa7`, with manifest SHA256`b093b65db5fc742063237fda234a0c6f42c614ffca799051d0550f6a1afa7747`. Prior qualified query contexts are read from the immutable own `bfd43fe406b72c7d4a4f5df492f42772fc4a60ba:docs/research/data/aux_saved_decisions_20261026/game-exposure.json.gz`, compressed-byte SHA256`20510b7d6985512057ae20af46b5ba86a8f2c98cefb5aa3055bb92b196d24062`. The exact repository path/blob and executed consumer hashes are in `data/aux_censored_paths_20261026/sources.json`.

The latest opening GitHub Pro review is sandbox`8edbf21d56b7df9b19fb09ad9ff63011e1f97021`, path`docs/reviews/chatgpt_patrol/2026-10-26_221052_JST_5f134bb.md`, blob`7d704214a796fed19a2fc5c0eca7e118e6ffca85`. Its AUX request refers to the earlierb2f3533bactive40.6177minute milestone; that proof/sign/history/censor task is already covered by the completed140a report. This new fallback keeps its independent source/history scope under the latest user's60+minute direction. It does not adopt PRIMARY's algorithm choice, PVS execution or320minute cap. Shared mainline runtime is unchanged; only the two existing AUX learner differences remain. GitHub Pro and Slack Dot were read separately. The new opening request was exact-payload reconciled; its single delayed read at14:11:07UTC found no reply. At the next meaningful closing interaction the late Dot reply1793023931.498049was privately saved and fully read. Its fixed-seat/actual-prefix/full-history/two-estimand cautions were adopted; the published implementation already independently enforced them before this read. Dot reported source-only review, not execution of our data/tests; this is not independent numerical replication.

## A hand-auditable prefix identity

Fix seat0. In the admitted finite deterministic two-seat zero-sum game, let V(h) be its true minimax WDL in{-1,0,1}, at the complete rule/history/clock context h. For a legal actual step h->h', acting regret is V(h)-V(h') at seat0and V(h')-V(h) at seat1. Bellman max/min makes each regret nonnegative and at most2. A single available ordinary action has regret0; declarations or other unaccounted choices invalidate that argument.

Summing any observed prefix from h0to hk gives:

```text
V(hk)-V(h0) = -Rseat0 + Rseat1.
```

No terminal endpoint, deterministic controller or memoryless TT assumption is needed for this path identity. The game itself and its complete history must have the stated semantics. Let D=Rbaseline-Rcandidate. If candidate occupies seat0, D=V(end)-V(start); if seat1, D=V(start)-V(end). For two paths from the SAME complete start, with candidate0in A and candidate1in B, equal weights give:

```text
D_A + D_B = V(endA)-V(endB).
```

At an actual Core terminal, V(end) is the actual terminal WDL. At an ongoing endpoint it remains unknown[-1,1]; heuristic/search/PV scores cannot replace it. Identical full endpoint contexts share the same V, so the observed-prefix contrast is exactly0. This is not a claim that the states or controllers have equal future actions, TT memory or realized returns.

In particular, two valid zero-move prefixes have prefix-regret contrast0while their eventual planned game-point completion bounds remain[0,1]. A missing path is different from an observed empty prefix: without a record there is no observed-prefix contrast to assign. If one recorded endpoint is terminal draw and its color mate is missing, the fixed two-slot mean game-point completion bounds are[1/4,3/4], not an observed score1/2or a one-game renormalization. Invalid/source-incompatible records also retain their planned slots but receive no actual WDL utility.

For a complete equal-weight swapped-seat pair, candidate mean terminal points are exactly `1/2+(D_A+D_B)/4`. Thus a pair contrast1and mean3/4are two encodings of the same outcomes. Summing the12old pairs gives total contrast2and overall mean `1/2+2/48=13/24`; the regret identity adds an interpretation, not an additional independent observation. This affine relation cannot be applied to ongoing endpoint potentials as if they were terminal policy returns.

## Unequal colors and timing filters

For weights wA/wB, the correct identity is:

```text
wA*D_A+wB*D_B = wA*V(endA)-wB*V(endB)+(wB-wA)*V(start).
```

Unknown root potentials therefore cancel only where complete-context coefficients actually cancel. Different physical/history contexts cannot be merged to force cancellation. The new consumer coalesces exact complete-context variables and reuses the existing rational interval arithmetic; it does not solve any unknown state or produce local action values.

| Descriptive target | Short / long recorded decisions | Total short-minus-long experienced WDL regret | Mean regret difference per retained decision |
|---|---:|---:|---:|
| All24complete games | 966 /965 | 2 | [94/466095,1/483] |
|23timing-qualified individual games | 919 /918 | [1,3] | [-793/843642,3/919] |
|11complete timing-qualified pairs | 872 /871 | 2 | [63/379756,1/436] |
|1930query timing mask, full histories retained for proof | 965 /965 | 2 | 2/965 |

The23-game target excludes game4but retains its swapped-seat mate. That root is n5-f2-h2at ply2, with fixed-seat0value v unknown[-1,1]. Its uncancelled coefficient is+1, so the target regret is2+v. The interval for its mean uses only this gap bound, nonnegative regrets and maximum2per nonforced move; unobserved game correlations may tighten it. An interval spanning0does not prove the actual mean reverses, and the endpoints are not feasible WDL assignments asserted for this RuleSet.

The individual-query mask is a different target. The sole timing-ineligible return is query371, game4, short policy, absolute ply65. Literal Core replay verifies exactly one ordinary legal move at that full record, matching the supplied move. Its regret is0even though the actual call failed its timing tolerance. Removing it algebraically from the FULL-path identity preserves total difference2and makes both denominators965, yielding2/965. The actual move must remain in record replay; deleting it from the trajectory would break the premise. This special zero-regret fact does not authorize dropping arbitrary overdue calls or repairing censoring by conditioning on observed timing.

The query control initially compared the raw diagnostic Action object to the GameRecord wire format directly. The test caught that representation mismatch; it now uses the existing diagnostic serializer/literal legal action, without changing source bytes. This was a consumer-test binding error, not evidence of an engine defect.

## Normalizing each color does not restore a common root distribution

If available color groups have root weights muA/muB, each normalized to sum1, their initial contribution is `sum_h (muB(h)-muA(h))*V(h)`. Since |V(h)|<=1, its magnitude is bounded by the L1distance of the FULL-context weight vectors, equivalently twice their total-variation distance. Matching a movement-family label or board image does not cancel this term. This is deterministic algebra; no independent-root sampling assumption is needed.

In the actual23-game timing subset, long occupies seat0in11games and seat1in12. Giving each group its own unit total weight leaves initial coefficient L1=1/6. The endpoint contrast is1/6, hence the sum-of-two-color-means regret contrast is only[0,1/3]. Explicitly, the11matched roots have coefficient-1/132each and the unpaired root has coefficient+1/12; their absolute sum is11/132+1/12=1/6. This makes the retained root uncertainty visible instead of hiding it in a normalized score. This is a different target from unnormalized23-game total[1,3]; it cannot be compared numerically without specifying weights. An independent discrete relaxation enumerated all531,441 assignments of12unknown root potentials in{-1,0,1}; its extrema0and1/3match the coefficient calculation. These are algebraic assignments, not game solutions or attainable minimax labels. All12matched roots with equal color weights would cancel the root terms exactly. The consumer retains exact rational weights rather than silently renormalizing a missing or invalid path.

## Actual outcomes and a hypothetical protocol-completion table are distinct

All24old games actually reached Core terminals: candidate(long) mean game points are13/24. The23whole timing-qualified games have actual mean25/46; conditioning changes the target population. Neither value is a new performance observation.

A separate fixed24-slot protocol-completion table may leave the one timing-inadmissible slot unassigned in[0,1], even though its actual terminal outcome remains known. That table mean lies in[25/48,9/16]. Independent arithmetic over the three possible WDL point entries0,1/2,1 gives exactly25/48,13/24,9/16. These are hypothetical completion-table bounds, not altered actual utilities, a qualifying rerun, a causal correction, or an assertion that any completion is attainable under this RuleSet/service protocol. They do not establish compliant equal-time policy strength.

Family4is fixed at3/4and families0,1,3,5at1/2. Family2has three qualified draws and the unassigned slot, giving[3/8,5/8]. Thus only1family is identified positive and at most2can be positive in this completion table. Filling this one inadmissible entry cannot produce three positive families in the OLD resource-arm contrast. A different prospective PVS intervention has unknown outcomes; the old table neither predicts it nor overrides a user's execution authorization. No source slot is refilled, relabelled or dropped.

## Every saved endpoint cut, with explicit limits

There are79,402ways to pair a prefix cut of each saved color mate, including its initial and terminal endpoints. They are retrospective views of the same24games, not new games, actual censoring frequencies, independent observations or a sampling distribution. Classification uses prior qualified incoming contexts; all24final records and96representative raw cut-record pairs are freshly replayed with the new consumer.

| Cut-pair class | Count |
|---|---:|
| Both ongoing | 77,459 |
| Exactly one terminal | 1,931 |
| Both terminal | 12 |
| Identical complete ongoing endpoint | 41 |
| Strictly positive regret lower bound | 2 |

With only complete-identity cancellation and actual-terminal endpoint values, the two strict positives are exactly the original two family4terminal pairs. Truncating or reweighting these records supplies no additional family with a strictly positive identified prefix contrast in this relaxation. This does not prove those other rules intrinsically drawn, deny useful search decisions, or rule out genuinely compatible supplied certificates.

Across these within-rule cut pairs,53same-physical-position matches have different complete records; one also has the same clock. Those are insufficient-key matches, not53proved WDL inequalities. The known equal-board/clock history example remains a negative control: its repetition maps differ, so the conservative prefix contrast remains[-2,2]. No TT/history quotient is introduced. Supplied empty PVs do not supply additional recorded endpoints or all-defense branches; the analysis uses actual GameRecords, not imagined continuations.

## A verified value relation is not a state or policy quotient

A supplied one-step record can support an exact equality without any numeric WDL label: if its parent has exactly one available ordinary action, V(parent)=V(child) at the SAME fixed seat. `verify_forced_link` checks the supplied parent/child records, full rule and one-step extension against Core. It fills no missing edge, rejects multiple-choice parents and external resignations, and creates no root/action value table.

Query371provides a real witness. Its parent at ply65has one legal action; the actual child at ply66has11. The parent's move is not legal in that child; position, history, clock and side-to-move differ. The true fixed-seat value equality therefore does not make them the same game state or a reusable move/TT identity. At opposite sides-to-move, actor-relative values also require sign conversion. Existing production search delegates identity to the public rule/position/clock/repetition/adjudication authority; TT entries carry depth, score, bound and best action, not this scalar WDL equality. No production identity guard is changed or weakened.

We checked whether sole-choice equality links alone could improve the two-color cut census. None of the41shared incoming contexts is forced. After the first different actual move, conservative full records never rejoin. Equality links restricted to supplied forced edges therefore cannot connect the two divergent branches. Further equality-closure engineering is not implemented for this cohort, and numeric terminal-value propagation to internal states is not performed. The checker is used only for the real timing-omission proof and its negative controls.

Forced regret0does not mean a timed search call is free, protocol-compliant or useless for learning. The real call still exceeded its timing tolerance. It may update TT/search memory relevant to later choices, and an observation on a forced path may still teach a learner about future outcomes. Skipping such a call is a different policy/execution protocol requiring its own evidence; this report proposes no optimization, training gate or speed claim.

The finite-source inability to manufacture more positive families also does not forbid an independently authorized bounded play experiment or make a universal solver a prerequisite. These are evidence/interpretation bounds, not a new registration, approval or rollout gate for PRIMARY.

## New Pro assignment: independent intake of the published PVS pilot

At the meaningful closing intake, sandbox advanced to `c695161cbc16fe5881773d4465ad00c1c5e1181e`. New Pro path `docs/reviews/chatgpt_patrol/2026-10-27_000503_JST_4f9f41e.md`, blob `04c08a48e883b84b90c178ae35bef5827102294e`, SHA256 `036d16ee367b6db3a26d4caf750b30ad6a85c589e353ba6fc9edba690b913117`, was saved before assessment. Adopted and executed its narrow AUX source/history task. PRIMARY's child-construction budget/algorithm choice remains outside AUX ownership. Shared production rules/search/runtime remain unchanged; no automatic remote code execution or infrastructure merge follows.

The new own `qualify_pvs_source_intake.py` reuses the existing context binder and literal GameSession replay. It checks the compressed/original hashes and byte lengths of the aggregate games, each of24individual game archives, executed source, plan, qualification and original-return archive. It also checks the executed input/plan hashes and every annotated query against its hashed original bytes. All six captured product source texts match the pinned published files after explicit LF normalization; this checks textual identity, not native-machine behavior. No archived producer/verifier code is executed. The first run exposed an omitted.jsonarchive suffix in this consumer and was corrected; it was not a defect in the published source.

The exact input gzip hash `dc471719ad6720f97be01b0a052cdc14728dfdab29dbe4b8bdb8a0785fb9dd93` matches the already qualified old resource-panel input:12rules,6families, same complete h2contexts. Prior full-rule H6 incompatibility remains applicable; repeating the old H6 solve or1931decision attribution is unnecessary. The twelve paired roots contain118legal root actions, all without supplied minimax labels. These are exposed development roots, not fresh rule generalization.

| Independently bound PVS source item | Result |
|---|---:|
| Actual saved games / complete swapped-seat roots |24/12|
| Actual Core DRAW: repetition / max-ply |4/20|
| Actual recorded game returns / D3qualification returns |2115/24|
| Caller status RETURNED |2115|
| Internal search termination cancelled / completed_depth |2075/40|
| Caller deadline observed |2075|
| PV present / empty |2089/26|
| Supplied PV plies counted, not freshly replayed |10738|
| Whole-game timing-qualified / complete qualified pairs |23/11|

All24final GameRecords are freshly replayed. All2115before/after query record hashes, saved action diagnostics and actor/policy assignments are bound to those exact records. Hash-qualified return bytes do not independently prove internal search behavior: all2115report runtime depth balanced, but live internal TT keys, bounds, controller memory and cancellation rollback are not snapshotted and remain NOT_VERIFIED. Presence/first-move checks of supplied PVs are distinct from Primary's reported interior-PV replay; this AUX intake does not repeat that replay or claim its10738plies as newly replayed.

Cancelled search termination is not a cancelled episode. These2075calls returned legal saved actions; every game reached an actual Core terminal. In particular max-ply is an actual rule DRAW, while the minimax value/quality of preceding decisions remains UNKNOWN. Neither a search score, empty PV nor identical terminal outcomes fills missing action truth.

The only timing-ineligible new query is `g1184`, game13/n6-f0-h2, OFF at ply80:1.1198712999466807seconds, caller deadline observed, internal termination cancelled. Its actual supplied full-history prefix was separately replayed: **three legal actions**, not a forced move. The old resource query371's forced-zero-regret exemption cannot be transferred. Dropping g1184 cannot be asserted to preserve the total regret identity, and timing noncompliance does not itself establish a bad action.

The PRIMARY frozen complete-pair convention leaves BOTH games12/13 unassigned, retaining24planned slots: ON mean completion bounds `[11/24,13/24]`; only family0can be positive, with its four-slot family interval `[1/4,3/4]`, and all other families fixed1/2. The possible strictly positive family count is[0,1]. A separately named single-ineligible-slot table would instead give `[23/48,25/48]`; it answers a different target and does not replace the frozen convention. The actual terminal mean remains1/2in either bookkeeping discussion. No score completion is asserted attainable or an equal-time rerun.

Three in-memory source negative controls independently reject a missing planned slot despite a recomputed manifest, a forged terminal winner despite recomputed aggregate/individual hashes, and corrupt gzip bytes. Exact source files remain untouched. These checks supplement200existing relevant regressions; they do not constitute new games, solver work, training labels or evidence that PVS improves strength.

The fresh follow-through measured a necessary coverage condition without propagating numeric truth. At each exact h2root, take the union of first actual actions in the old resource games, first actual actions in the new PVS games, and the new D3qualification choices. Each selected diagnostic action is checked against that root's freshly replayed full legal frontier. Across all12roots this union contains16of118legal actions, leaving102unobserved; **zero roots have a complete root frontier**. `pvs-root-coverage.json.gz` retains every root's counts; it is not another1931decision attribution or an additional solver.

Relative to the14old actual root actions, only two selected choices add union coverage: n5-f2-h2adds one D3qualification choice that was not actually played in either PVS color game; n6-f5-h2adds one actual PVS choice. The union therefore mixes actual play and qualification returns under different budgets/arms. Its16covered choices measure exposure only, not16good actions, causal PVS effects or improved decision quality.

This excludes treating these selected returns as a complete action-value table or an all-choice root certificate. It does NOT exclude a valid one-sided OR-node bound or a partial strategy certificate: a lower-bound strategy may need one root action and all relevant defender replies, not every alternative root action. Even complete root action coverage alone would not establish child values or all-defense completeness below that root. The chosen next AUX route is therefore to consume an actually supplied compatible certificate/quality endpoint, while preserving UNKNOWN where absent; it is not to demand a universal full-frontier solve before prospective play. Different source prefixes may have shared actual edges, but root family names cannot substitute for full RuleSet/history binding.

Next use is compatibility of a genuinely new supplied full-history/action certificate or quality endpoint. The current packet supplies no numeric minimax action label and no cross-family positive score. This is an evidence boundary for interpreting these records, not a prerequisite or new approval gate imposed on PRIMARY.

## Verification, cost and next source

`scripts/paired_path_bounds.py` reuses bind_context, actual GameSession/Core replay and linear_interval_bounds. It separates complete episode contrast, observed prefix contrast, requested observed-path targets and fixed planned game-point completions. `scripts/analyze_censored_leaper_records.py` binds the immutable PRIMARY manifest and own qualified source before computing the cut census and timing populations.38new actual-source controls plus162existing choice/exposure/regret/history checks pass:200total. Extra heuristic/terminal/PV metadata cannot label an ongoing actual record. Controls include policy sign reversal, exact weights, missing/invalid slots, unequal initial histories, one-ply-before-mate UNKNOWN, forced timing omission and separate whole-game timing flags. No result is a new heldout or training label.

The original209.50498295related minutes, previous105.402minute whole session window, actual closing delivery and this round's real costs remain carried. No new round name resets a frozen experiment cap. Admin, transport, idle/offline and unconfirmed interrupted intervals earn no research credit. At this milestone f34f609f remains ACTIVE with68.70282confirmed effective minutes; source-bound work continues toward the user's60Ã¢â‚¬â€œ90minute requirement. Current tasks remain ownWORK_PLAN/NEXT_WORK, not the hourly prompt.

Closing communication: milestone3befdd2cdcb2fb0175e6f9107be3cd5e5ca18c0awas pushed and full remote SHA verified before followup1793028676.485069at15:31:16.485069UTC. The single delayed complete-thread check at15:36:55UTC (due15:36:16UTC) found no new reply; the supplied-certificate question remains pending, not a gate or expired request. No empty polling or repeated send. Late opening Dot reply was adopted as conceptual source review, not numerical replication.
