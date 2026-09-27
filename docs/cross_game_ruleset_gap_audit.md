# Cross-game RuleSet capability audit

**Scope.** This is a rule-semantics audit, not a material-score experiment or a
claim of full game support. The single unknown is which general primitives are
still needed to express and execute the chess-family cases the user named.
The minimum direct observation is a source-to-schema/compiler/executor check and
paired legal-action tests. Full games and self-play cannot answer that question
more directly.

The 2018 WXF Xiangqi coverage is tracked separately in
`xiangqi_2018_rule_coverage_matrix.md`. Its 9×10 diagnostic RuleSet executes
ordinary actions in Python Core but is not a registered product ruleset;
history-based WXF adjudication and native parity remain open.

## Janggi as a distinct semantics probe

The [Japan Shogi Association's world-games rules summary](https://isf.shogi.or.jp/en/special/world.html)
describes Janggi on a 9×10 board with palace diagonals, blocked Horse and
Elephant paths, Chariot diagonals within a palace, a Cannon that must jump one
piece for both quiet movement and capture, a prohibition on jumping over or
capturing a Cannon, Soldier forward/sideways movement plus forward palace
diagonals, optional pass, and different draw conditions. This secondary rules
summary is a starting source for paired tests, not a tournament adjudication
oracle. Rule variations and outcome details require a chosen authoritative
ruleset before claiming a complete Janggi implementation.

The [Korea Janggi Association's piece-movement page](https://koreajanggi.cafe24.com/business/business3.php)
describes the Elephant as one straight step followed by two diagonal steps,
with an occupied route square preventing the move. The bounded fixture below
tests one orientation of that route, not every orientation or tournament rule.

| Generic capability | Present evidence | Smallest missing observation or change |
|---|---|---|
| Rectangular board and initial pieces | `RuleSet.board_width/board_height`; Xiangqi 9×10 diagnostic executes | Retain 8×8 Chess and 9×9 Shogi behavior while exercising 9×10 Janggi templates. |
| Horse/Elephant blockers | Xiangqi diagnostic uses path constraints for Horse leg and Elephant eye. `tests/test_janggi_palace_chariot_diagonals.py` verifies a Janggi Elephant (2,3) template with separate guards at both intermediate squares; open route succeeds and blocking either square independently rejects it for both owners. | No new primitive is needed for this tested orientation. Other Elephant orientations and integration into a complete authoritative ruleset remain unverified. |
| Palace-only edges | `tests/test_janggi_palace_chariot_diagonals.py` verifies a 9×10 unregistered fixture: both owners in both palaces can move Chariot corner↔center and across a clear corner-to-corner diagonal; a center blocker stops the long ray; off-palace sources/targets and side-edge off-line diagonals are rejected. A one-step royal diagonal uses the same cross-zone guard. `apply_action` is checked; native compilation fails closed on square-zone guards. | No new generic primitive is needed for this tested diagonal subset. Native parity and integration with a complete authoritative Janggi ruleset remain unverified. |
| Cannon screen count and type | Verified in `tests/test_janggi_cannon_guard_composition.py`: `path_count_eq=1` plus `count(Cannon, path_between)=0` rejects a Cannon screen for quiet and capture actions; a target-square guard rejects Cannon capture. Both owners execute on 9×10 Python Core. A 10×10 square diagnostic matches native guarded actions. | No new primitive needed for this rule. Rectangular 9×10 native execution remains unavailable, so the square native check is not a Janggi product parity claim. |
| No-board-change action | `tests/test_no_board_change_action_gap.py` confirms `RuleSet` and the public `Action` union expose no pass opt-in/action. Existing identity already includes side-to-move: same board with opposite side has another key, and two hypothetical passes return to the initial key for repetition counting. Core transition, history provenance, search runtime, and session serialization have no pass branch. | A complete vertical slice needs a distinct no-square `PassAction` plus explicit opt-in and legal-pass guard across public/semantic movegen, apply/history/terminal, and every action consumer; repetition can reuse position keys. Consecutive-pass adjudication must remain a separately specified policy, not an implicit game-name rule. |
| Selectable setup | `RuleSet.initial_position` is one fixed position | If players can choose Horse/Elephant layouts, define a generic pre-game setup choice rather than hard-coding the game name. A set of separate frozen RuleSets is only a diagnostic substitute. |
| Conditional outcomes | Generic repetition/draw and no-move policies are narrow; WXF history adjudication is open | Specify facts and declarable precedence for facing-anchor, consecutive-pass and scoring outcomes before implementing a particular federation's policy. Do not equate Xiangqi's facing-General check with Janggi's outcome rule. |

## Implementation order

1. Prove each missing rule with one pair of tiny positions where only the
   relevant condition changes. Prefer composition of existing typed guards;
   extend the DSL and Python executor only for a demonstrated gap. Compiler
   rejection of unsupported native behavior must remain explicit.
2. Bring native execution to parity for an added primitive before registering
   a product ruleset that may select the native path. Test active and inactive
   cases, then re-run Chess and Standard Shogi retention tests.
3. Build an unregistered Janggi diagnostic only after these primitives exist.
   Compare sampled legal move sets against an independent identified engine or
   rule oracle. Keep history adjudication and competition conventions explicit
   rather than silently treating them as ordinary move legality.

Optional rules must be selected at compile time; absent pass, zones, blocker
type filters or history policies should not add work to the ordinary Chess and
Shogi move path. This is a design requirement pending a measured hot-path
check, not a proven performance result.
