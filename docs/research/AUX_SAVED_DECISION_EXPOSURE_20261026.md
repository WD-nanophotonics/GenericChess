# Saved Leaper decisions: identified differences and useful exposure

Status: scientific milestone in active DEV_AUX session140a989c. No60minute completion is claimed at this checkpoint.

The two saved root-ordering experiments have no single-decision minimax action-value difference at their matched completed depths: all corresponding selected actions are identical. Absolute action quality remains unknown. The separately saved resource-control games contain informative outcome contrasts, but only one observed movement family supplies them. They do not evaluate an equal-time algorithm change.

## Fixed source and execution scope

PRIMARY source: `fd7d7eacbdc2741e766f26b67b0f54018a998aa7`; Pro review: `68f83ff02067b7d557b12eb1438e066504bfa192`, `docs/reviews/chatgpt_patrol/2026-10-26_200745_JST_fd7d7ea.md`, blob `76d2dad6d0c710cf6ad89db549415b3b3cb63229`. The remote sandbox ref was explicitly fetched and compared with the prior covered version. The source manifest SHA256 is `b093b65db5fc742063237fda234a0c6f42c614ffca799051d0550f6a1afa7747`. Every consumed gzip is checked against that immutable manifest before decoding. See machine-readable source pins below.

AUX replays full RuleSet/GameRecord/current-state/frontier bindings. Returned search-input attribution remains the published driver/input-hash claim; matching a legal returned move is not a cryptographic observation of the historical process. Stored original return bytes and all before/after record hashes, seats, clocks, actual actions and supplied PV moves are checked independently by this consumer. No Player, new solver, game, build, training, optimization or production/default change is launched. Source status remains AVAILABLE_SOURCE_NOT_ASSIGNED. H6/H64 truth is not transferred.

## Fixed-depth comparisons

For full context h and legal action a, Q*(h,a) denotes the acting seat's WDL under minimax continuation after that one move. Q*(h,a)-Q*(h,a)=0 without knowing Q*. This is not equality of the controllers' subsequent play or proof that a is optimal. Missing/failed returns have no observed action-value estimand: intervals for possible legal completions preserve the planned denominator without assigning an actual WDL or protocol utility.

| Phase | Baseline → comparator | Depth | Planned / legal pairs | Same / changed | Mean single-decision difference |
|---|---|---:|---:|---:|---:|
| phase1 | baseline → scan_hint | 1 | 24 / 24 | 24 / 0 | [0,0] |
| phase1 | baseline → scan_hint | 4 | 24 / 24 | 24 / 0 | [0,0] |
| phase2 | original → record_only | 4 | 24 / 24 | 24 / 0 | [0,0] |
| phase2 | original → record_only | 6 | 24 / 24 | 24 / 0 | [0,0] |
| phase2 | original → work_order | 4 | 24 / 24 | 24 / 0 | [0,0] |
| phase2 | original → work_order | 6 | 24 / 24 | 24 / 0 | [0,0] |
| phase2 | record_only → work_order | 4 | 24 / 24 | 24 / 0 | [0,0] |
| phase2 | record_only → work_order | 6 | 24 / 24 | 24 / 0 | [0,0] |

Phase1 has48original same-depth pairs. Phase2 has48three-arm groups: record-only is the observer control, work-order is the candidate, and original→work-order is a derived pairwise contrast. The three pairwise views are not three independent experiments. Phases/depths are not pooled. All240returns completed their requested depth and selected legal actions. Nominal search time limits are not formal whole-call eligibility thresholds; their outer-time comparison is labelled descriptive. The separate game timing tolerance is never imported into this table.

Across the same baseline contexts, D1→D4 changes12/24actions (outer mean bound[-1,1]); D4→D6 changes7/24 ([-7/12,7/12]). These are exposed depth-sensitivity diagnostics, not additional algorithm experiments or signs of improvement. Equal search scores do not label different actions; changed depths/scores do not establish useful changes.

The source retains24preparation-v1failures and the corrected v2inputs; these are preparation failures, not lost or refilled Player slots. All source comparisons explicitly usePVS ON, while the production default isPVS OFF. Native flags are requested by the historical drivers; this analysis makes no new Native service/speed claim. Resource games use separate seat Players, cold TT per game and persistent TT between that seat's moves. Later matched choices therefore compare the whole resource/TT protocol, not just the current call's budget.

## Actual source exposure and the prefix denominator

All24saved games contain1931recorded decisions. There are1890distinct conservative full-record decision contexts,147forced decisions with one legal ordinary move, and1784multi-action decisions. A forced move has zero action regret in this move/declaration-free domain; multiple legal moves only allow a quality distinction, they do not prove one. No action WDL is inferred from the eventual game result. The original24roots contain254UNLABELLED actions.

The game design uses12h2contexts, not all24prepared h2/h3contexts. On those12fixed initial roots, long/short budgets choose the same first action10times and different actions twice: the root-side single-decision mean interval is[-1/3,1/3]. This is an interval relaxation for those fixed roots, not a confidence interval, overall policy value or an equal-time algorithm comparison. The h3contexts have no game observation. The two actual long-policy wins occur in family4, whose initial action is identical between budget arms; this illustrates why root-action equality does not imply equality of continuation outcomes.

There are41full-context long/short observations:29same actions plus12first divergences. They are not41preplanned independent quality pairs. For each color pair, if L actual moves are initially equal and the next moves differ, conservative full-record matching yields exactly L+1shared query contexts: Lsame choices and one differing choice. After that divergence the full records never rejoin, even when positions repeat. Thus the denominator is mechanically affected by agreement.

| Source context | Equal actual prefix L | Shared query contexts | First divergences |
|---|---:|---:|---:|
| n5-f0-h2 | 4 | 5 | 1 |
| n5-f1-h2 | 6 | 7 | 1 |
| n5-f2-h2 | 2 | 3 | 1 |
| n5-f3-h2 | 5 | 6 | 1 |
| n5-f4-h2 | 5 | 6 | 1 |
| n5-f5-h2 | 1 | 2 | 1 |
| n6-f0-h2 | 1 | 2 | 1 |
| n6-f1-h2 | 0 | 1 | 1 |
| n6-f2-h2 | 2 | 3 | 1 |
| n6-f3-h2 | 0 | 1 | 1 |
| n6-f4-h2 | 1 | 2 | 1 |
| n6-f5-h2 | 2 | 3 | 1 |

315position groups contain distinct full contexts. One observed group additionally has the same complete rule, position, absolute clock and legal frontier, but different incoming repetition-count maps: queries129and223 in n5-f1, ply11. Their selected actions differ. This is a checked historical alias, not proof of different minimax values or a causal effect of history: budget, search memory and trajectories differ too. No history merge is authorized.

33returns contain an empty PV despite a legal selected action and a completed iteration. The initial adapter wrongly required a nonempty PV; it was corrected without modifying the source. Default require_full_pv=False and the published negamax TT-return paths permit best_action with an empty continuation. This source reading establishes a possible mechanism, not attribution of every empty return: per-return TT contents are unavailable. All9636supplied PV-occurrence plies are checked (9630unique after exact-prefix/PV deduplication); empty PVs explicitly supply no continuation. Legality of a supplied PV never makes it an all-defense certificate.

## What the terminal contrasts actually identify

The following is a finite-game algebraic consequence of the SAME observed outcomes, not an independent strength experiment or new local WDL labels. Preconditions: identical full initial context, deterministic finite two-seat zero-sum WDL rules, actual Core/Session rule terminals, and exactly swapped long/short seats. Source rules have a96ply cap and no declaration/restart action; all final records replay. Caller truncation, no-contest, resignation/declaration replacing a Core terminal, different histories/rules or a missing color mate cannot use this inference.

Fix seat0and let V*(h) be its minimax WDL. Define acting-player regret r(h,a)=V*(h)-V*(ha) at seat0, and V*(ha)-V*(h) at seat1. Bellman max/min implies r≥0; each r is0,1or2. Telescoping any complete actual path gives z=V*(h0)-R0+R1, where z is its actual fixed-seat terminal WDL and Rp sums that seat's regrets along its visited states. This uses no heuristic score and makes no claim that a played continuation was minimax.

For gameA(long seat0) and gameB(long seat1), the identical initial V* cancels:

```text
zA = V* - Rlong,A + Rshort,A
zB = V* - Rshort,B + Rlong,B
zA-zB = (Rshort,A+Rshort,B) - (Rlong,A+Rlong,B).
```

Identical actual prefix moves contribute identical acting regrets but opposite policy credits across the two games, so their contributions also cancel. A positive margin therefore forces at least one nonoptimal short-policy move somewhere in the divergent suffixes; forced one-action decisions can be excluded. This does not identify which move, prove the long policy optimal, compare per-decision averages, or generalize beyond these visited states. Equal terminal outcomes imply equal total policy-attributed regrets, not zero absolute regret.

| Source pair | Fixed-seat0 outcomes A/B | Short-minus-long total actor regret | Known nonoptimal short choices | Possible nonforced short suffix slots |
|---|---:|---:|---:|---:|
| n5-f0-h2 | 0 / 0 | 0 | not located/proved | not restricted |
| n5-f1-h2 | 0 / 0 | 0 | not located/proved | not restricted |
| n5-f2-h2 | 0 / 0 | 0 | not located/proved | not restricted |
| n5-f3-h2 | 0 / 0 | 0 | not located/proved | not restricted |
| n5-f4-h2 | 0 / -1 | 1 | at least1 | 52 |
| n5-f5-h2 | 0 / 0 | 0 | not located/proved | not restricted |
| n6-f0-h2 | 0 / 0 | 0 | not located/proved | not restricted |
| n6-f1-h2 | 0 / 0 | 0 | not located/proved | not restricted |
| n6-f2-h2 | 0 / 0 | 0 | not located/proved | not restricted |
| n6-f3-h2 | 0 / 0 | 0 | not located/proved | not restricted |
| n6-f4-h2 | 0 / -1 | 1 | at least1 | 67 |
| n6-f5-h2 | 0 / 0 | 0 | not located/proved | not restricted |

Across all12pairs, total short-minus-long experienced actor regret is exactly2WDLunits; the11complete timing-qualified pairs have the same contrast2. The two positive pairs are both family4, different board sizes. Each contains an existential nonoptimal short-policy decision among52and67candidate slots respectively. No individual member is labelled wrong, no root value is solved, and no family is selected for optimization. The119candidate slots are exposed, correlated source traces, not independent samples or oracle-selected training starts. Actual query timing qualification is1930/1931, game qualification23/24, color qualification11/12; the timing-ineligible pair is retained in the all-source result.

## Alternatives examined and current use

An off-policy estimator is not implemented. Dudík, Langford and Li describe contextual-bandit DR using a reward model plus action propensities; Jiang and Li extend the approach to sequential decisions with trajectory likelihood ratios and independence requirements. These source logs supply neither calibrated action-selection probabilities nor a validated target-policy reward/value model. A wall budget or two observed actions is not a propensity. Game contexts are endogenous, and persistent TT state and the whole budget protocol affect later choices. Empirical prefix overlap cannot repair those assumptions. This is a rejection of a log-only DR strength estimate here, not a claim that values are mathematically unidentifiable from a fully known finite RuleSet. [Dudík et al., ICML2011](https://icml.cc/2011/papers/554_icmlpaper.pdf), [Jiang and Li, ICML2016](https://proceedings.mlr.press/v48/jiang16.pdf).

The other considered shortcut is to reuse H6/H64 truth or treat a terminal game/PV/search score as a local minimax certificate. It is rejected: the12current H96/repeat4fingerprints differ, and legality plus one played line does not cover all defenses. Current output retains UNKNOWN and the exact source scope. Useful next work can consume genuinely compatible published certificates or a new assigned full-history source; this analysis does not launch a solver or repeat the closed audit. PRIMARY owns future algorithm/quality design and defaults.

## Verification and reproducibility

Source metadata and gzip hashes are in data/aux_saved_decisions_20261026/sources.json. Results: matched-choices.json.gz and game-exposure.json.gz in the same directory. Scripts: scripts/score_published_leaper_choices.py and scripts/audit_published_leaper_exposure.py. The former reuses the existing bound_same_context_pairs consumer, rather than creating another bound implementation. The latter only replays stored actions/PVs and computes source support and the conditional regret identity.

Targeted controls cover missing/failed slots, strict rotation IDs, malformed/foreign actions and fingerprints, empty PVs, unsupported terminals, original-return corruption, full-record hashes, seat/clock/policy/timing errors, shared-prefix stopping and regret-sign orientation. Test fixtures are explicitly derived published slices, not new trials or independent holdouts. The original adapter refusal and its correction are preserved privately. 135relevant tests pass (74targeted source/exposure/contrast controls plus61shared truth-consumer controls). The actual full-data replay used the current script source. Session/publication receipts will replace this active milestone status at closure.

Prior related full-chain lower-bound cost209.50498295minutes is retained, plus this round's actual cost; the user's direct continuation authorization is not re-requested. Configuration, communication/publication and idle time do not count as research. No frozen experiment cap or prior failure is reset.
