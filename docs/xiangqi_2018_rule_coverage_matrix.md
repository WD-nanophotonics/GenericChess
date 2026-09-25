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
| Board, setup, side-to-move; ordinary quiet moves, captures, occupancy and rays (§§2.1, 2.4) | `tests/test_xiangqi_diagnostic_semantics.py` exercises an internal, unregistered 9×10 semantic RuleSet through compile → initial_state → legal_actions/apply_action, with exact standard 32-piece coordinates and public initial action set. Initial `legal_actions` move set matches Fairy-Stockfish 14 LB `UCI_Variant=xiangqi`, `startpos`, `go perft 1` exactly (44/44; empty symmetric difference); local oracle binary SHA-256 `2FE12FF0FCAD0295482CAB7660E1FCC24259CEBC4EF164839FB16C9F9CABFC99`. This is one initial-position comparison only, not broad Xiangqi validation. | Yes / Yes / Narrow Python semantic Core path / Integrated diagnostic cases; initial position independently cross-checked | Legacy square compilation and native execution remain disabled for rectangular semantic rules; this diagnostic builder is not product registration. |
| General/advisor palace bounds; elephant river restriction (§§2.1–2.3) | The diagnostic RuleSet applies palace confinement to General/Advisor and home-side zone plus eye blocking to Elephants; public behavioral tests cover both owners. | Yes / Yes / Narrow Python semantic path / Integrated synthetic ruleset cases; no independent WXF oracle | Native semantic execution fails closed for square-zone guards. |
| Horse-leg and elephant-eye blockers (§§2.3, 2.5) | Diagnostic public behavioral tests verify both owners' Horse-leg and Elephant-eye blockers. | Yes / Yes / Narrow Python semantic path / Integrated synthetic ruleset cases; no independent WXF oracle | Native semantic execution is fail-closed for its square-zone guards. |
| Soldier forward-only before river, lateral moves after river, no promotion (§2.7) | Public diagnostic tests verify forward-only before crossing, lateral moves after crossing, both owners, and no promotion on the 9×10 ruleset. | Yes / Yes / Narrow Python semantic path / Integrated synthetic ruleset cases; no independent WXF oracle | Native semantic execution is fail-closed; history adjudication is outside this diagnostic. |
| Cannon quiet ray vs capture over exactly one screen (§2.6) | Diagnostic public-action tests verify both owners, zero/one/two screens, quiet movement blocked by a screen, and capture removal without hand transfer. | Yes / Yes / Narrow Python semantic path / Integrated synthetic ruleset cases; no independent WXF oracle | Native semantic execution remains unsupported for the required semantic guards. |
| Facing generals, check, self-check legality, checkmate (§§2.1, 2.8–2.10) | Diagnostic public tests verify facing-General check for both anchors, screen blocking, screen-removal self-check rejection, safe screen shifts, and exclude non-General ray targets through full legal-action generation. | Yes / Yes / Narrow Python semantic path / Integrated synthetic ruleset cases; no independent WXF oracle | Checkmate and history-based WXF outcomes are not validated; native semantic execution remains fail-closed. |
| No legal move is a loss, including stalemate (§2.11, Article 3.1.A.II) | Generic `RuleSet.stalemate_result` accepts `draw` or `loss`; public Core/semantic terminal paths carry the winner, and both UI result panels display it. `tests/test_mate_stalemate.py`, `tests/test_rule_semantics_ir_hardening.py`, and `tests/test_ui_redesign.py` cover synthetic behavior. Native compilation remains fail-closed for `loss`. | Yes / Yes / Yes, generic product path / Yes, synthetic cases only; no Xiangqi behavior oracle | Generic stalemate-loss behavior is now executable and tested, but no integrated Xiangqi ruleset or WXF position validates the rule combination. This row does not establish complete Xiangqi support. |
| Repetition and perpetual check (§§19.8–19.9) | Position history/repetition and `continuous_check_loss` exist; Shogi product exercises the latter. See `tests/test_repetition.py` and `tests/test_standard_shogi_product.py`. | Partial / Partial / Partial / Chess+Shogi only | Current policy choices are `draw` or `continuous_check_loss`; a recurring WXF cycle must be classified from the repeated move history, not just assigned Shogi's continuous-check rule. |
| Perpetual chase and other prohibited repeated actions (§§19.6–19.12) | History is available to adjudication, but no generic chase classification / chased-piece-set primitive was found in `RuleSet`, IR, or terminal logic. | No complete declaration / No / No / No | WXF distinguishes check, chase, and other move classes, with outcomes depending on which side repeatedly violates the rule. This is the clearest missing history semantic; do not approximate it as generic repetition draw or continuous-check loss. |
| Chess and Standard Shogi retention | Existing executable builders and product tests: `tests/test_western_chess_product.py`, `tests/test_standard_shogi_product.py`, `tests/test_repetition.py`; Shogi also has drop/promotion and its 500-ply adjudication product tests. | Yes / Yes / Yes / Yes, within those tests | These demonstrate current product retention for the tested built-ins; they do not verify Xiangqi or certify all FIDE/WXF competition procedures. |

## Finding and next bounded observation

The diagnostic builder is an internal, unregistered 9×10 RuleSet with public
Python semantic-Core tests for the listed ordinary movement, capture, blockers,
palace/river conditions, facing Generals, self-check, and no-legal-move loss.
This remains a synthetic diagnostic rather than a product ruleset or an
independent WXF oracle. WXF repetition/perpetual-check/chase adjudication and
The initial legal move set agrees with the identified Fairy-Stockfish build, but
that comparison does not independently validate later positions or conditional
legality. Independent boundary-position oracle coverage and WXF
repetition/perpetual-check/chase adjudication remain absent; this is not complete
WXF Xiangqi support.

The public diagnostic tests check setup coordinates, both owners' movement and
blocking, complete public action generation without pattern-ID filtering, a
successor transition, and illegal-action rejection. Python semantic execution
works through IR validation; native payload construction remains fail-closed
for square-zone guards. This does not enable legacy square APIs or establish
complete WXF Xiangqi support.
