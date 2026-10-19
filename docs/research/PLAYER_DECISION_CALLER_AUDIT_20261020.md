# Public PlayerDecision caller audit and asymmetric-drop preflight — 2026-10-20

## Caller-audit conclusion

The bounded source inventory found no second backend gameplay/benchmark caller
that discards AlphaBeta declarations or adjudicates an external cutoff as a
rule draw. The paired benchmark runner and AlphaBeta CLI now preserve explicit
`DECLARATION` decisions; learning arena/self-play already applies a returned
`declaration_id` through `GameSession.declare()`. The Shogi lazy-history audit
uses the legacy `learning.shogi_rules.build_shogi_ruleset()` fixture, which has
no declaration definitions, and records search counters rather than outcomes.
Native-readiness telemetry serializes `decision.action` as a field, but its
fixed `_hb` rulesets have no declarations and it does not apply/adjudicate a
game. `scripts/unfamiliar_search.py` validates PV/action legality and records
decisions; it does not apply moves or score game outcomes. These are scoped
source findings, not a proof over arbitrary external callers.

`UIController.finish_ai_move` still submits only a non-null ordinary action.
For declaration-capable imported rules, the UI can therefore leave the session
ongoing and request another AI decision. This is a real known UI integration
limitation, but UI Test is user-maintained and outside this backend lane; no UI
source, branch or tests were changed. Backend declaration support is not a
claim of end-to-end UI declaration support.

## New price-question preflight

Question: can asymmetric owner-specific drop permissions make a shared static
hand-piece price materially misleading, and would evidence justify owner-aware
price inputs? A read-only 4x4 legacy rook fixture was copied in memory with
owner 0's rook-drop mask empty and owner 1's mask full. With the same kings and
one rook in hand for the side to move, owner 0 had 3 legal actions and no rook
drops; owner 1 had 17 legal actions, including 14 rook drops. Yet the current
profile assigned both states a side-to-move static hand score of +900 and the
same base-type hand value of 900. The profile's `drop_freedom_ratio` and
`drop_mobility` are diagnostics built from owner-0 masks, while `Evaluator`
uses one `hand_value_by_base_type` for either owner.

This is a controlled structural counterexample to owner-aware evaluation,
not evidence that owner-specific prices improve outcomes. One asymmetric
synthetic fixture does not establish generated-rule frequency, a correct price
delta, finite-budget utility or a default change. Next action is a minimal
decision-changing utility witness under matched search conditions, reusing
this fixture; first look for an existing reachable rule/position and avoid new
games or training unless the witness cannot be resolved cheaply.

## Reproduction and scope

The source paths are `generic_chess/ai/evaluation/profile.py` (`_drop_profile`
reads owner 0; `build_ruleset_profile` builds one hand-value table) and
`generic_chess/ai/evaluation/evaluator.py` (both hand owners index that same
table). The diagnostic used `tests/ai_fixtures.py::build_4x4_rooks`,
`tests/conftest.py::make_state`, `generic_chess.core.movegen.legal_actions`,
and an in-memory `dataclasses.replace` of the compiled drop masks. It wrote no
source or data files. A separate attempt to apply this diagnosis to the
semantic Standard Shogi product ruleset was correctly rejected by the current
static-profile metadata guard; this preflight therefore makes no claim about
semantic-only profile behavior.

## Generated-domain boundary and exact-signature transfer check

The owner-asymmetric fixture is schema-valid but is not produced by the current
generic generator. `generic_chess/generation/generator.py` derives each owner's
drop mask from the same owner-relative movement atoms, and
`core.coordinates.relative_to_absolute` maps the two owners by 180-degree
rotation. Therefore generated drop masks are rotation-equivalent; a read-only
scan of the 29 existing JSON rule records found no exception. The synthetic
owner-0/owner-1 hand-value gap does not justify changing prices for the stated
generated-rule domain. It remains an explicit boundary for arbitrary hand-
authored asymmetric RuleSets.

I then compared exact movement-signature classes across all 16 existing frozen
5x5 profiles (`521001`–`521008` and `522001`–`522008`). There are 48 non-anchor
entries and 46 classes. The only cross-rule exact class is `profile-521004:P`
and `candidate96/profile-522008:A`; both are promotable and share the exact
signature `[["L",1,0],["R",-2,1,-1]]`. Their raw capability scores are
identical (`1.3468429710250438`), while normalized board/hand values are
`615/554` versus `1000/900`. The rules' raw-score medians differ: `2.188674`
versus `1.346843`, which explains the normalized value change. The only other
repeated class is two types inside rule 521005, not a cross-rule match. Input
SHA256s: `profile-521004.json`
`90ab29a9810a4b636ed5b6c190991584cfedf93633b17d3cba6d742529d0fd03`;
`candidate96/profile-522008.json`
`ba6da0917c9b675c41a18235765e8bd704331ae6c8dc8063e4342a5129af8441`.

This supports a narrow conclusion: the geometry-only raw score is stable for
this exact signature, but the published integer price is intentionally relative
to each ruleset's ordinary-piece composition. One cross-rule pair cannot
establish a global price law, utility benefit or default change. No games,
training or source code changed. A cheap next discriminator is to compare raw
and current-normalized profiles at the same saved roots/rules and equal node
caps; only an action change would justify considering any later utility panel.
