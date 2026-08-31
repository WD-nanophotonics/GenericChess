# ADR-090: Standard Shogi 500-move product integration

Status: Accepted for F29 product integration

## Decision

The live Standard-Shogi RuleSet adopts one `RuleAutomaticAdjudication` with
id `standard_shogi_500_move_no_contest`, `trigger_ply=500`, outcome
`NO_CONTEST`, and continuation policy
`threshold_actor_continuous_check`.  The certified F28 evaluator remains the
sole implementation; `standard_shogi.py` contains only the product
definition.  Existing `max_ply=512` is retained and is suppressed only while
the threshold checking extension is pending.

The product fingerprint changes from the pre-rule F27 value to the frozen F29
value.  Metadata remains fingerprint-neutral and records that the move-500
rule is supported, while bilateral agreement, automatic replay creation, side
reversal, and time-control administration remain outside the current
GameState/session boundary.

NO_CONTEST is re-derived from ordinary actions and existing history.  Game
Record schema v1 therefore remains sufficient for ordinary action replay; no
special no-contest marker is added.  Session and AlphaBeta roots expose the
generic terminal result, and non-mate terminal children are valued through
the terminal score (zero for no-contest), before declaration assessment.

The F27 below-threshold search corpus remains historical evidence.  Re-running
its exact 30 fixed-node rows with the new product identity produced identical
action, score, PV head, and completed-depth parity across two fresh repeats;
the durable summary is
`tests/fixtures/f29_standard_shogi_500_move_product_search_results.json`.

## Boundary

F29 certifies the engine/session/search product rule, not tournament-complete
Shogi administration.  Native semantic completeness remains unsupported for
this declaration- and automatic-adjudication-bearing product.  The next
boundary is external AlphaSho reference benchmarking (F30); Article 9(4)
agreement and replay administration are not part of this decision.
