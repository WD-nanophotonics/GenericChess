# 2018 WXF Xiangqi rules: generic support coverage

**Order:** `CAUSAL_DIAGNOSTIC` — single unknown: where declarable, compilable,
executable, and verified support diverge for the fixed 2018 WXF Xiangqi ruleset
while preserving current Chess and Standard Shogi behavior. Minimal observation:
compare the rule clauses with the existing schema, compiler, executor, and focused
tests. Full games are unnecessary because the unknown is representational and
rule-execution coverage, not playing strength.

**Scope:** WXF, *World Xiangqi Rules* (2018), principally Chapter 1 §§2.1–2.11,
Chapter 1 Article 3.1.A, and Chapter 4 §§19.8–19.10. This is position/move and
game-history adjudication only; clock, touch-move, arbiter procedure, and other
tournament administration are excluded. [Official WXF English rules (PDF)](https://www.wxf-xiangqi.org/images/wxf-rules/2018_World_XiangQi_Rules_English2018.pdf).

Stage meanings: **D** = declarable in `RuleSet`/semantic DSL; **C** = accepted
by a compiler into the relevant IR/product representation; **E** = can be
executed by the public product path; **V** = covered by a relevant behavior
test (not just a schema or compile-only fixture). `Partial` never means full
WXF Xiangqi support. A test-only/static carrier is not product support.

| 2018 WXF rule family | Generic primitive / evidence | D / C / E / V | Current blocker and smallest evidence-backed note |
|---|---|---|---|
| Board, setup, side-to-move; ordinary quiet moves, captures, occupancy and rays (§§2.1, 2.4) | `RuleSet` has rectangular width/height, initial position and piece types. `tests/test_rectangular_public_semantic_execution.py` exercises only synthetic 9×10 leap moves, transitions, and an occupancy guard through public compilation/Core APIs; it does not verify a Xiangqi setup, capture, or ray rule. `tests/test_xiangqi_static_setup_fixture.py` remains explicitly incomplete and test-only. | Yes / Partial / One narrow Python semantic Core path / Synthetic rules only | The tested reference-executor path is not a complete Xiangqi ruleset or WXF behavior oracle. Legacy square compilation and native execution remain disabled for rectangular semantic rules. |
| General/advisor palace bounds; elephant river restriction (§§2.1–2.3) | Explicit square zones and spatial selectors exist (`RuleSpatialSelector`); per-side move geometry and zone state can be described. | Yes / Partial / No full Xiangqi path / No Xiangqi behavior oracle | Palace/river restrictions need correct side-relative 9×10 masks and executable integration. No supported Xiangqi preset or rule-level tests were found. |
| Horse-leg and elephant-eye blockers (§§2.3, 2.5) | `RulePathConstraint` supports constrained paths. The public synthetic 9×10 test runs an owner-relative source-offset occupancy guard through compile → initial state → legal actions and proves blocked/unblocked behavior for both owners. B4b compile-only seam tests remain separate. | Yes / Partial / Narrow synthetic path-guard execution / Synthetic blocker test | This verifies only the tested leap-plus-guard combination, not Xiangqi horse/elephant rules as a whole. Unsupported semantic predicates remain fail-closed; broader composition/guard combinations need their own evidence. |
| Soldier forward-only before river, lateral moves after river, no promotion (§2.7) | Typed zones/state guards and ordinary owner-relative leaps are available declaratively; no public 9×10 behavior test for this combination is included in the current probe. | Yes / Partial / Not verified / No Xiangqi behavior oracle | Requires phase-dependent move filtering over the two sides' river masks. The narrow rectangular semantic Core path exists, but this Soldier combination and a complete Xiangqi setup are not behavior-verified. |
| Cannon quiet ray vs capture over exactly one screen (§2.6) | Rays, occupancy relations and counted path constraints are generic primitives; no public 9×10 behavior test for this combination is included in the current probe. | Yes / Partial / Not verified / No Xiangqi behavior oracle | Must distinguish unobstructed quiet movement from a capture with exactly one intervening occupied point and stop at the first eligible target beyond it. The narrow rectangular semantic Core path exists, but this rule combination is not behavior-verified. |
| Facing generals, check, self-check legality, checkmate (§§2.1, 2.8–2.10) | Generic anchors, attack generation and self-check filtering exist (`core/attacks.py`, `core/terminal.py`). | Yes / Partial / No full Xiangqi path / Chess behavior tests only | The primitives are plausible for the facing-file constraint if encoded as ordinary attacks, but the whole 9×10 Xiangqi product is not executable and no Xiangqi regression verifies that encoding. |
| No legal move is a loss, including stalemate (§2.11, Article 3.1.A.II) | Generic terminal logic distinguishes no legal action while checked (mate) from not checked (stalemate); `RuleSet.stalemate_result` can syntactically store a value, but the compiler accepts only `draw`. | Storable / No for loss / No for WXF outcome / No Xiangqi test | WXF treats stalemate as a loss, unlike the current v0 supported `draw` result. The compiler rejects other outcomes (`STALEMATE_RESULT_UNSUPPORTED`). |
| Repetition and perpetual check (§§19.8–19.9) | Position history/repetition and `continuous_check_loss` exist; Shogi product exercises the latter. See `tests/test_repetition.py` and `tests/test_standard_shogi_product.py`. | Partial / Partial / Partial / Chess+Shogi only | Current policy choices are `draw` or `continuous_check_loss`; a recurring WXF cycle must be classified from the repeated move history, not just assigned Shogi's continuous-check rule. |
| Perpetual chase and other prohibited repeated actions (§§19.6–19.12) | History is available to adjudication, but no generic chase classification / chased-piece-set primitive was found in `RuleSet`, IR, or terminal logic. | No complete declaration / No / No / No | WXF distinguishes check, chase, and other move classes, with outcomes depending on which side repeatedly violates the rule. This is the clearest missing history semantic; do not approximate it as generic repetition draw or continuous-check loss. |
| Chess and Standard Shogi retention | Existing executable builders and product tests: `tests/test_western_chess_product.py`, `tests/test_standard_shogi_product.py`, `tests/test_repetition.py`; Shogi also has drop/promotion and its 500-ply adjudication product tests. | Yes / Yes / Yes / Yes, within those tests | These demonstrate current product retention for the tested built-ins; they do not verify Xiangqi or certify all FIDE/WXF competition procedures. |

## Finding and next bounded observation

The immediate gap is not piece labels or a missing Xiangqi preset. One small
synthetic 9×10 RuleSet now has a tested public Python semantic-Core path,
including an occupancy-guard witness. This does not establish other rectangular
rule combinations or the full Xiangqi rule set: WXF-specific stalemate/history
outcomes and an integrated ruleset oracle remain absent. Consequently there is
no complete, executable, verified 9×10 WXF Xiangqi ruleset today.

The bounded public executor probe checks row-major targets, both owners' source-
relative blocker behavior, initial-position validation, a successor transition,
and rejection of an illegal action. The Python reference semantic capability is
enabled only through `compile_semantic_ruleset` after IR validation; legacy and
native capabilities remain false. This narrow result does not enable the legacy
square APIs or establish complete Xiangqi support.
