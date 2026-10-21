# Assessing the incoming general-game MCTS suggestion

Date: 2026-10-21. This note assesses an incoming project Chat comment attributed in its message text to Claude. The connected Chat uses a shared account, so the attribution is not independent identity verification. The exact project-related incoming read remains privately preserved in ignored `.local_agent`.

The suggestion was to consider a no-training UCT/MCTS baseline, Fairy-Stockfish as a chess-like comparator, and rigorous paired, budgeted evaluation that keeps UNKNOWN outcomes explicit and reports rule-family results and actual cost. Methodologically, those evaluation safeguards are sound. Fairy-Stockfish can answer a separately scoped chess-variant interoperability question, but does not cover the complete generated GenericChess rule domain.

## Existing MCTS work is related, not a drop-in baseline

The repository already contains `SemanticGumbelMCTSV0` in `generic_chess/learning/gumbel_mcts.py`. It uses Native semantic actions, a Gumbel-root / sequential-halving policy, and fixed 16- or 64-simulation budgets with at most eight root candidates. Its intended learning route uses a policy and value checkpoint. `policy=None` is a uniform-prior smoke mode; with no checkpoint, leaf values are zero. It does not perform terminal random rollouts and is not equivalent to the proposed no-training UCT baseline. It returns `GumbelSearchResult`, not the public `ai.Player` `PlayerDecision`, and the current production callers do not consume it.

The prior F115â€“F121 Shogi Gumbel work should not be repeated. Its experiment reports have been removed from the active tree by the authorized 2026-10-21 cleanup; the current [retired cleanup manifest](https://github.com/WD-nanophotonics/GenericChess/blob/62b2a02a7e9c1d867935104f95b3003401c350ad/docs/operations/CLEANUP_20261021_FILES.json) records their removal, while their committed versions remain in Git history. The historical sequence was: F115/F116 rejected; the F118 child failed its F119 Arena4; F120 became invalid after a neutral declaration; F121 added the neutral-declaration outside option and passed its four-pair Arena4. That small result did not automatically promote the candidate or establish generic-domain performance.

## Bounded terminal-only UCT stability checks

The candidate tested here is a separate, private terminal-only UCT prototype over Core `legal_successors`, with uniform random rollouts up to the authoritative 512-ply cap, root action chosen by maximum visits, and UNKNOWN retained rather than assigned a score. The experiments are two 6x6 generated `bilateral_random` action-only roots (seeds 7 and 21), with 17 and 19 legal root actions. They had no declarations, auxiliary state, semantic actions, or automatic adjudications; no root promotion/drop action was legal. Although their rule definitions allowed capture-to-hand/drop and promotion, this sample does not exercise the full GenericChess domain.

At two seconds per root, UCT completed only two simulations and one UNKNOWN rollout per root. At 25 seconds, it completed 23 and 46 simulations, with one UNKNOWN each. Three independent 25-second repetitions per same root selected two distinct actions for seed 7 and three for seed 21; the maximum-visit child had only 2â€“8 visits. Thus the fixed-action random-continuation outcomes are not evidence of MCTS strength.

A prespecified fixed-simulation follow-up tested 64 and then 128 terminal-only simulations per search, three independent RNG seeds per root. The per-run seed is `79102621 + rep*1009 + int(fingerprint[:8],16)`, using the root-specific fingerprint and repetition index. All six runs at each budget completed with no UNKNOWN. Each root still selected three distinct actions across its three repetitions: at 64 simulations the winning child had 6â€“8 visits; at 128 it had 14â€“23 visits. The exact protocols and per-run actions/visit counts are available in [`data/terminal_uct_stability_20261021/`](data/terminal_uct_stability_20261021/). The 64/128 runner was executed inline and was not saved as a standalone script; the protocol, result rows, and base implementation SHA are retained, so the procedure is auditable but not directly rerunnable from a checked-in runner. The fixed-128 batch took 677.29 seconds under its 1,200-second hard cap.

These are stability screens on two roots, not independent ruleset-level strength estimates. No games, training, product change, or full head-to-head arena were added. The 25-second random continuations averaged 173.8 plies after the UCT opening and 158.7 after the AlphaBeta opening; these are only rough per-ply cost proxies, not engine-match lengths. At 25 seconds of search per played ply, the observed maxima exceed 120 minutes, so a future run expected to reach that threshold requires the user's necessity assessment before it starts.

## Decision

Adopt the comment's methodological safeguards: explicit UNKNOWN, matched per-decision budgets, independent rulesets as the inference unit, per-root results and cost, and no strength claim from a single selected opening action followed by random play. Defer a no-training UCT Player integration: action stability alone supplies no evidence of utility through 128 simulations, there is no current production caller, and the complete generated-rule domain is not covered. Do not start training, repeat the frozen Gumbel arenas, add a Player adapter, or promote a default from this evidence. Return to the current `LOCAL_MAINLINE.md` requirement for a distinct, decision-changing finite-budget contract with a named live caller.


## Later correction —2026-10-21

Claude explicitly corrected the missing-MCTS claim. The two-root UCT screen is
not a Gumbel comparison or a reason to claim Gumbel lacks utility. The existing
Gumbel backend had a separate, now reproduced winner-propagation defect; see
[the actual repair and decision-region study](PRICE_DECISION_REGIONS_20261021.md).
Its no-checkpoint leaf is zero, and the cited Gumbel policy-improvement argument
requires action-value conditions; no generic strength or adapter adoption follows.
Keep UNKNOWN distinct: prospective generator draw rules are new game definitions,
not instructions to impute old capped outcomes.
