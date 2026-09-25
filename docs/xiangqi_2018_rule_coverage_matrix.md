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
| Board, setup, side-to-move; ordinary quiet moves, captures, occupancy and rays (§§2.1, 2.4) | `RuleSet` has rectangular width/height, initial position and piece types; movement atoms include leap/ray. `tests/test_xiangqi_static_setup_fixture.py` explicitly says its Xiangqi fixture is incomplete and test-only. | Yes / Partial / No full Xiangqi path / Static fixture only | The geometry carrier and compile-only rectangle work do not amount to a public executable 9×10 ruleset. Public rectangular compilation is explicitly rejected by `tests/test_compiled_geometry_catalog_b2.py` and `tests/test_rectangular_semantic_action_b4b.py`. |
| General/advisor palace bounds; elephant river restriction (§§2.1–2.3) | Explicit square zones and spatial selectors exist (`RuleSpatialSelector`); per-side move geometry and zone state can be described. | Yes / Partial / No full Xiangqi path / No Xiangqi behavior oracle | Palace/river restrictions need correct side-relative 9×10 masks and executable integration. No supported Xiangqi preset or rule-level tests were found. |
| Horse-leg and elephant-eye blockers (§§2.3, 2.5) | `RulePathConstraint` supports constrained paths; B4b has a fail-closed compile-only lowering for one source-relative, zero-occupancy offset guard. See `tests/test_rectangular_semantic_action_b4b.py` (compile-only horse-leg test). | Yes / Partial / No / Compile-only guard test | The tested lowering is narrowly static and public rectangular semantic execution remains closed. Multiple guard/template ambiguity is intentionally rejected. |
| Soldier forward-only before river, lateral moves after river, no promotion (§2.7) | Typed zones/state guards and ordinary owner-relative leaps are available declaratively. | Yes / Partial / No full Xiangqi path / No Xiangqi behavior oracle | Requires executable phase-dependent move filtering over the two sides' river masks. Current compile-only support is not an executable Xiangqi rule. |
| Cannon quiet ray vs capture over exactly one screen (§2.6) | Rays, occupancy relations and counted path constraints are generic primitives. | Yes / Partial / No / No Xiangqi behavior oracle | Must distinguish unobstructed quiet movement from a capture with exactly one intervening occupied point and stop at the first eligible target beyond it. The current rectangular path is not product-executable. |
| Facing generals, check, self-check legality, checkmate (§§2.1, 2.8–2.10) | Generic anchors, attack generation and self-check filtering exist (`core/attacks.py`, `core/terminal.py`). | Yes / Partial / No full Xiangqi path / Chess behavior tests only | The primitives are plausible for the facing-file constraint if encoded as ordinary attacks, but the whole 9×10 Xiangqi product is not executable and no Xiangqi regression verifies that encoding. |
| No legal move is a loss, including stalemate (§2.11, Article 3.1.A.II) | Generic terminal logic distinguishes no legal action while checked (mate) from not checked (stalemate); `RuleSet.stalemate_result` is restricted to `draw` by `rules/compiler.py`. | Yes (declared default) / No for loss / No for WXF outcome / No Xiangqi test | WXF treats stalemate as a loss, unlike the current v0 supported `draw` result. The compiler rejects other outcomes (`STALEMATE_RESULT_UNSUPPORTED`). |
| Repetition and perpetual check (§§19.8–19.9) | Position history/repetition and `continuous_check_loss` exist; Shogi product exercises the latter. See `tests/test_repetition.py` and `tests/test_standard_shogi_product.py`. | Partial / Partial / Partial / Chess+Shogi only | Current policy choices are `draw` or `continuous_check_loss`; a recurring WXF cycle must be classified from the repeated move history, not just assigned Shogi's continuous-check rule. |
| Perpetual chase and other prohibited repeated actions (§§19.6–19.12) | History is available to adjudication, but no generic chase classification / chased-piece-set primitive was found in `RuleSet`, IR, or terminal logic. | No complete declaration / No / No / No | WXF distinguishes check, chase, and other move classes, with outcomes depending on which side repeatedly violates the rule. This is the clearest missing history semantic; do not approximate it as generic repetition draw or continuous-check loss. |
| Chess and Standard Shogi retention | Existing executable builders and product tests: `tests/test_western_chess_product.py`, `tests/test_standard_shogi_product.py`, `tests/test_repetition.py`; Shogi also has drop/promotion and its 500-ply adjudication product tests. | Yes / Yes / Yes / Yes, within those tests | These demonstrate current product retention for the tested built-ins; they do not verify Xiangqi or certify all FIDE/WXF competition procedures. |

## Finding and next bounded observation

The immediate gap is not piece labels or a missing Xiangqi preset. Some useful
geometry/history primitives are declarable and some compile into static or
square-board paths, but the public rectangular executor and WXF-specific
stalemate/history outcomes are absent. Consequently there is no complete,
executable, verified 9×10 WXF Xiangqi ruleset today.

Smallest next generic compiler task: determine whether the already-lowered
single source-relative occupancy guard can cross the public rectangular
compile/execute boundary using a synthetic, game-name-independent 9×10 ruleset.
Keep it to one blocker guard and a paired positive/negative move-generation
test, plus existing Chess/Shogi retention tests. This isolates the next
compiler/executor seam; it does not claim to solve cannon movement, Xiangqi
history adjudication, or authorize scoring/benchmarking Xiangqi.
