# Existing playability preference: cost and diagnostic opportunities — 2026-10-18

Keep `require_no_opening_win_in_one` as an optional sampler for future development diagnostics, with its changed rule distribution stated explicitly. This finite survey finds more usable structural choices after short random prefixes, at a modest absolute generation cost, but it does not establish balanced games, stronger play or better learning. The generator default is unchanged and existing fitness is never filtered retrospectively.

## Question and prospective controls

The new price-transfer panel retained6terminal roots out of32, producing624 zero-query deployments. Before generating further fitness, examine the **existing** exact one-ply preference across a broader generator grid. The source already checks whether the actual opening player has a winning legal first action; it does not promise a long or balanced game.

The registration fixes64new seeds431001–431064 × board sizes4/6/8 × classic-like/free-random setups × bilateral/no movement symmetry. Hybrid movement is allowed. Each of768seed/condition pairs is generated once with the preference off and once on, alternating flag order by seed parity. The whole pair order is shuffled with a fixed seed. Each generation has16attempts, a deliberate bounded survey setting; the normal1000-attempt default is not changed. All refusal outcomes remain.

Promotion, drops, auxiliary state and full relevant history are retained. From each successful rule, the same deterministic random stream advances through prefix targets0,4,16, stopping at actual terminal states. Save each complete record, witnesses, outcome and all legal-child material vectors, promotion/drop availability and exact one-ply winning actions. These are structural opportunities; they are not actual search-selected TD gradients or fitness outcomes.

The complete1,536 calls finish in214.016seconds within the original1800second/1GiB cap. There are1,533 successful generations, three filtered16-attempt refusals, no missing calls and4,599 saved full-state observations. The observations are not all distinct states. Unfiltered succeeds768/768 and filtered765/768. Among765both-success pairs,606accept the same complete rule and159replace it. Every same-rule pair has identical full records, states, witnesses and material diagnostics at all three prefixes. Including the three refusals, the preference rejects162initially accepted default rules with a winning first action.

This is a paired **intention-to-generate** grid. A preference may reject a rule and accept a later different rule from the RNG stream; that comparison changes the sampling measure rather than changing the behavior of one fixed game. An observed generation refusal supplies zero available diagnostic observations, not a game draw. Missing unattempted calls would remain unknown; none occurred.

## Results and actual costs

| Finite grid metric | Preference off | Preference on |
|---|---:|---:|
|Successful generation|768|765|
|Prefix4 still ongoing|722|751|
|Prefix16 still ongoing|640|688|
|Prefix16 raw child-material contrast|615|660|
|Prefix16 actual drop action available|363|399|
|Prefix16 actual promotion action available|324|327|
|Measured generation seconds, all calls|7.289|18.684|
|Measured diagnostic seconds, successful calls|81.657|84.581|

The prefix16 ongoing increase is48/768=6.25percentage points, with a descriptive fixed-grid seed-block95envelope[4.04,8.59]points. Raw child-material contrast increases45/768=5.859points, envelope[3.65,8.20]. At prefix4 the corresponding increases are3.776 and3.255points. The block resampling retains all twelve conditions and both flags for each seed; it is not population confidence over generated games. Every condition, refusal and terminal-prefix observation remains in the complete analysis.

Filtering costs roughly2.56times the generation time **in this run**, an absolute11.395seconds extra across768pairs. Whole producer time also includes semantic compilation, full-state recording and analysis preparation. Per-case generation/diagnostic clocks omit some of those costs; the whole214.016seconds is larger than their sum. Concurrent machine load and alternating order do not make these clocks a causal speed benchmark. No retry beyond16attempts is hidden in the cost.

## Terminal-aware interpretation

Raw material counts can be nonzero in an actual terminal state. That does not create a learnable terminal leaf: the established terminal-constant/zero-own-gradient rule still applies. Likewise, having differently valued child material does not matter to an immediate winning terminal action that dominates ordinary material.

A separate post-survey diagnostic therefore recomputes **all** saved legal children, without new samples, games or search. It distinguishes nonterminal child vectors and removes actual one-ply winning choices from an “unforced ordinary-material contrast” counter. Raw records/features are retained; they are not zeroed or relabelled.

| Prefix | Ongoing root with nonzero material, off/on | Distinct ordinary-child contrast, off/on | Immediate winning child, off/on | Unforced ordinary contrast, off/on |
|---|---|---|---|---|
|0|0 / 0|594 / 596|162 / 0|474 / 596|
|4|479 / 497|667 / 692|85 / 55|582 / 637|
|16|609 / 653|615 / 660|49 / 48|566 / 612|

This shows why balanced initial material alone is an inadequate “no information” test: legal successor features can differ even while the initial signed count vector is zero. It also prevents counting nonzero **terminal** material as an eligible learning root. The prefix16 unforced contrast increases46/768; it remains a one-ply structural availability observation. Deeper search may select terminal continuations or erase a difference; no training improvement follows from these counts alone.

The finite prefix16 gain appears in every board-size, setup and symmetry marginal for ongoing/ordinary contrast. That does not eliminate cross-condition variation or prove universal usefulness. The three bounded refusals, additional attempts, replacement-rule bias and altered representation of promotion/drop branches must accompany any future sampler use.

## Verification, source and decision

Independent Core reconstruction checks all4,599 complete saved records,28,933recorded plies and101,545legal-child transitions. A separate Counter-based CURRENT-board/BASE-hand projection agrees on every saved material vector count, legal-action count, terminal result, state/witness hash and promotion/drop count. The first reader takes170.773seconds; this is source reconstruction using Core, not an independent rules implementation.

The16-payload1,298,785byte capsule is SHA256 `122458e96c04d4a33f71adc399f89f4231c3763aedbc0722b0530f630367dd19`. It includes all rules, successes/failures, complete records, raw clocks, scripts and the later opportunity registration. Its explicit source dependency is the fixed movement capsule; all ten actual generation Python modules were checked equal to that source modulo newlines. Fresh extracted-source reader/analysis/opportunity qualification passes in342.344seconds: all three saved outputs are parked before regeneration, Native is absent, module origins and real caller stop flags are checked, and every non-time field plus the original raw clock values matches. No generation, fitness or training producer is rerun during qualification.

For future **diagnostic** generation, this optional preference is worth retaining as a candidate because it cheaply removes an observed source of trivial opening decisions while preserving all accepted rule semantics. It is not a default change, a definition of the whole generic task, a quality label for rejected games, or permission to discard failures from a study. A future learning comparison must independently freeze whether it samples the default or conditioned rule measure, keep its costs and evaluate actual gains. Existing AUX and DeepSeek experiments remain untouched.

[Complete finite summaries](data/playability_filter_20261018) · [Raw records, source dependency and reproduction](../archive/playability_filter_20261018) · [New-rule transfer context](NEW_RULE_PRICE_TRANSFER_20261018.md).


## Actual Native selected-leaf input diagnostic

A distinct post-survey question asks whether structural availability translates into returned material derivative inputs for ONE unfitted Unit checkpoint. All4599 saved full observations are used, including265 actual terminal roots. Every actual nonanchor type has independent board-CURRENT/hand-BASE channels; no type/history truncation, new generation, fitness game, TD update or auxiliary learning. Native256 D2/32768nodes/.5s/q0/TT0; one active rule/engine at a time. No ordering checkpoint is supplied.

All4599 points return in83.460s:4334 usable Native queries, all completedD2,3671686nodes,0refusal/incomplete/fallback,2653 nonzero chosen-leaf gradients. A terminal leaf uses its actual scoring constant0/±1 and zero own gradient; its raw material vector is preserved. Nonterminal prediction is tanh(sum(phi)/10), derivative phi*(1-prediction²)/10. No TD residual or eligibility trajectory is computed. Unit ties mean this is the derivative for the selected leaf, not a claim of a unique root derivative.

| Prefix | Nonzero chosen-leaf gradients: unfiltered | Filtered |
| --- | ---: | ---: |
|0|181|214|
|4|505|556|
|16|574|623|

Each column starts from768 intended generation slots; bounded generation refusals are unavailable inputs, not measured zero gradients. Prefix16's49 extra available nonzero inputs are6.3802 percentage points of that intended denominator. All ongoing roots here have owner0 because prefixes are even; do not extrapolate to both roles or a population. The measure changes with accepted rules and trajectories. Availability does not demonstrate better updates, calibration, WDL or learning gain.

Independent Counter-based Core replay reconstructs all4599 roots/4334queries/8265PVedges, all features, terminal constants, predictions and gradients;427 actual terminal leaves have zero own gradient. Its57.152s check uses no Native query. The [new capsule](https://github.com/WD-nanophotonics/GenericChess/blob/b942f11e50e20689d4455c5b4dc2d00ea0985b89/docs/archive/filter_native_inputs_20261018/README.md) pins both the complete filter-survey input capsule and fixed backend source; extracted source parks and regenerates the reader without Native. Original raw query clocks are retained, not independently remeasured. Earlier producer parse/record preparation errors occurred before queries and were preserved privately; no frozen run or cap was restarted.

Decision remains an OPTIONAL diagnostic sampling candidate. No generator default, current learner, AUX task or model was changed. Before a future training comparison, preserve intended-slot refusals, the changed accepted-rule measure, total generation/input costs, and a frozen independent objective; this study alone is not a training selection result.


A separate post-seal paired decomposition checks the mechanism of this availability difference. All606 identical complete-rule pairs match on root hashes, chosen actions/PVs, node counts, leaf features/predictions and gradients at all three prefixes. Prefix16's net49 inputs decompose as0 from same-rule pairs,+51 from159 rule replacements and-2 from3 bounded generation refusals. Prefix4 is0/+53/-2; prefix0 is0/+33/0. Thus the observed increase comes from selecting different accepted rules, with a real refusal cost, rather than improving search inputs for an unchanged game. This favors explicit distribution-aware sampling comparisons over a claim of stronger learning. The [paired script/result](https://github.com/WD-nanophotonics/GenericChess/blob/b942f11e50e20689d4455c5b4dc2d00ea0985b89/docs/research/data/filter_native_inputs_20261018/paired-input-decomposition.json) are post-seal additions, separately regenerated exactly against extracted pinned source/inputs with Native absent; the sealed7-payload capsule was not rewritten.
