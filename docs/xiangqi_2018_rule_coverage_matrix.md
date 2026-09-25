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
| Board, setup, side-to-move; ordinary quiet moves, captures, occupancy and rays (§§2.1, 2.4) | `tests/test_xiangqi_diagnostic_semantics.py` exercises an internal, unregistered 9×10 semantic RuleSet through compile → initial_state → legal_actions/apply_action, with exact standard 32-piece coordinates. Independent Fairy-Stockfish 14 LB perft-1 comparison (`UCI_Variant=xiangqi`, binary SHA-256 `2FE12FF0FCAD0295482CAB7660E1FCC24259CEBC4EF164839FB16C9F9CABFC99`) covers 7 hand-constructed single-ply positions and 32 positions along four fixed-seed 8-ply paths (seeds 11, 23, 37, 53): 39 comparisons; every move set matched exactly and both directional differences were empty. Reproduction script is transient/ignored at `.generic_chess_flow/oracles/compare_xiangqi.py`; it invokes `go perft 1`, not full games. | Yes / Yes / Narrow Python semantic Core path / Integrated diagnostic cases plus sampled independent move-set checks | Sampled positions do not establish all Xiangqi legality or history adjudication; legacy square compilation and native execution remain disabled, and the diagnostic builder is not product registration. |
| General/advisor palace bounds; elephant river restriction (§§2.1–2.3) | The diagnostic RuleSet applies palace confinement to General/Advisor and home-side zone plus eye blocking to Elephants; public behavioral tests cover both owners. | Yes / Yes / Narrow Python semantic path / Integrated synthetic ruleset cases; no independent WXF oracle | Native semantic execution fails closed for square-zone guards. |
| Horse-leg and elephant-eye blockers (§§2.3, 2.5) | Diagnostic public behavioral tests verify both owners' Horse-leg and Elephant-eye blockers. | Yes / Yes / Narrow Python semantic path / Integrated synthetic ruleset cases; no independent WXF oracle | Native semantic execution is fail-closed for its square-zone guards. |
| Soldier forward-only before river, lateral moves after river, no promotion (§2.7) | Public diagnostic tests verify forward-only before crossing, lateral moves after crossing, both owners, and no promotion on the 9×10 ruleset. | Yes / Yes / Narrow Python semantic path / Integrated synthetic ruleset cases; no independent WXF oracle | Native semantic execution is fail-closed; history adjudication is outside this diagnostic. |
| Cannon quiet ray vs capture over exactly one screen (§2.6) | Diagnostic public-action tests verify both owners, zero/one/two screens, quiet movement blocked by a screen, and capture removal without hand transfer. | Yes / Yes / Narrow Python semantic path / Integrated synthetic ruleset cases; no independent WXF oracle | Native semantic execution remains unsupported for the required semantic guards. |
| Facing generals, check, self-check legality, checkmate (§§2.1, 2.8–2.10) | Diagnostic public tests verify facing-General check for both anchors, screen blocking, screen-removal self-check rejection, safe screen shifts, and exclude non-General ray targets through full legal-action generation. | Yes / Yes / Narrow Python semantic path / Integrated synthetic ruleset cases; no independent WXF oracle | Checkmate and history-based WXF outcomes are not validated; native semantic execution remains fail-closed. |
| No legal move is a loss, including stalemate (§2.11, Article 3.1.A.II) | Generic `RuleSet.stalemate_result` accepts `draw` or `loss`; public Core/semantic terminal paths carry the winner, and both UI result panels display it. `tests/test_mate_stalemate.py`, `tests/test_rule_semantics_ir_hardening.py`, and `tests/test_ui_redesign.py` cover synthetic behavior; `tests/test_xiangqi_diagnostic_semantics.py` also checks no-legal-move loss in the internal Xiangqi diagnostic builder. Native compilation remains fail-closed for `loss`. | Yes / Yes / Yes, generic product path / Yes, synthetic and internal diagnostic behavior; not WXF-adjudication validated | The internal diagnostic ruleset exercises the outcome, but WXF history adjudication remains absent; this does not establish complete Xiangqi support. |
| Repetition and perpetual check (§§19.8–19.9) | Generic 9×10 identity/count bookkeeping is tested by a reversible two-rook cycle; a legal unilateral check cycle also exercises public `apply_action` and generic `continuous_check_loss`. A separate synthetic mutual-check fixture tests only generic repetition-draw fallback and is not WXF-legal. Chess/Shogi history coverage remains in `tests/test_repetition.py` and `tests/test_standard_shogi_product.py`. | Partial / Partial / Partial / Generic identity/count and unilateral check loss tested; WXF mutual-cross-check legality and adjudication unverified | Generic repetition/counts do not establish WXF classification. Mutual-check fallback is synthetic only; chase/block/exchange/offer rules remain absent. |
| History-based move classification and WXF adjudication (§§19.1–19.19, 20.1–20.10) | See [`xiangqi_2018_history_semantics.md`](xiangqi_2018_history_semantics.md) for the clause-by-clause facts/policy map, existing history/replay evidence, official example anchors and fail-closed gaps. No generic chase classifier, stable chased-piece identity, cycle-pattern precedence or WXF outcome policy exists today. | Partial position/history substrate / No WXF adjudicator / No WXF adjudicator / Ordinary move-set oracle only | WXF examples distinguish check, chase, exchange, block, offer, root/protection and mixed sequences; repetition count alone cannot adjudicate them. Do not approximate WXF as `continuous_check_loss` or generic repetition draw. |
| Chess and Standard Shogi retention | Existing executable builders and product tests: `tests/test_western_chess_product.py`, `tests/test_standard_shogi_product.py`, `tests/test_repetition.py`; Shogi also has drop/promotion and its 500-ply adjudication product tests. | Yes / Yes / Yes / Yes, within those tests | These demonstrate current product retention for the tested built-ins; they do not verify Xiangqi or certify all FIDE/WXF competition procedures. |

## Finding and next bounded observation

The diagnostic builder is an internal, unregistered 9×10 RuleSet with public
Python semantic-Core tests for ordinary movement, capture, blockers,
palace/river conditions, facing Generals, self-check, no-legal-move loss, and
rectangular position-identity/repetition-count bookkeeping. It remains a
synthetic diagnostic rather than a product ruleset or a full WXF implementation.
The 39 sampled move sets agree with the identified Fairy-Stockfish build, but
that comparison does not exhaust later positions or history-dependent
conditional legality. WXF perpetual-check/chase adjudication remains absent.

The public diagnostic tests check setup coordinates, both owners' movement and
blocking, complete public action generation without pattern-ID filtering,
successor transitions, repetition identity/count updates, and illegal-action
rejection. Python semantic execution works through IR validation; native
payload construction remains fail-closed for square-zone guards. The standard
evaluation-profile builder currently cannot construct a profile for this
rectangular semantic compiler (`AttributeError: piece_types`). A one-node-bound
Alpha-Beta probe with a neutral stub evaluator entered `negamax` but failed in
the default `MoveOrderer.order` at `state.position.board_size()` with
`ValueError: board_size is undefined for a rectangular position`; it produced
no search result or meaningful score. Other square-size call sites were not
exercised and are deferred to Priority 2. This does not establish complete WXF
support.
