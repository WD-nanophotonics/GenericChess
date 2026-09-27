# WXF 2018 history semantics: bounded design and evidence

**Order:** `CAUSAL_DIAGNOSTIC`. Single unknown: for Chapter 4 Articles 19–20,
which adjudication inputs are replayable facts of a generic game history, which
are rule-set policy, and what is missing from the current history interface?
Minimal observation: map each rule family to its needed positions, actions,
cross-ply evidence, exceptions and current Core support. No complete game is
needed; no adjudicator is implemented here.

**Source:** World Xiangqi Federation, *World Xiangqi Rules* (2018), Chapter 4,
Articles 19–20, printed pp. 35–39 (PDF pp. 43–47). [Official WXF English rules
(PDF)](https://www.wxf-xiangqi.org/images/wxf-rules/2018_World_XiangQi_Rules_English2018.pdf).
The local reference copy used for visual inspection is
`.generic_chess_flow/wxf_2018_reference.pdf` (SHA-256
`2B45534953BBFCCA42DC2C52E06BE48FF44EBE3BF7237248B12E39576C494CF3`). Fairy-
Stockfish move-set comparisons elsewhere do not validate WXF history rules.

## What history currently contains

`GameState` in `generic_chess/core/position.py` carries the current `Position`,
`ply_count`, repetition counts, terminal result and an ordered history. Each
`HistoryRecord` stores a stable position key, actor, canonical action signature
and `gave_check` boolean. The key covers ruleset identity, side to move, board
piece fields, hands and semantic auxiliary state. Semantic `apply_action` in
`generic_chess/core/transition.py` appends the record and derives `gave_check`
from the resulting position.

For a complete history that replays from `initial_state`, `SearchPathRuntime`
in `generic_chess/core/search_runtime.py` can reconstruct exact prior positions
by parsing the canonical action signatures and reapplying generic transitions;
it verifies every produced record and the final state. A custom/imported root
or incomplete/mismatched history without trusted Core-supplied position
witnesses falls back to opaque identities rather than fabricated positions.
There is no persistent piece-instance ID or generic move-nature/chased-target
record. However, opt-in `reconstruct_history_provenance` assigns ephemeral
piece identities when complete history replays exactly;
`capture_pressure_trace` and `trace_next_turn_legal_captures` join those
identities to pseudo-capture and counterfactual legal-capture facts.
`tests/test_xiangqi_actual_path_target_identity.py` verifies those legal edges
on the Xiangqi path for two same-type targets that occupy the same square at
different plies. `tests/test_xiangqi_repeated_target_cycle_identity.py` adds
two legal diagnostic cycles. A four-ply control retains the same chaser and
target token across its capture edges. An eight-ply cycle returns to the same
position and repetition key but has a same-type target on the same square for
one edge; the trace distinguishes the tokens. This establishes only that
existing replay and identity-aware legal-capture facts expose token changes.
The second cycle is not a WXF-valid negative chase example: after the rook
threatens target A on ply 2, the reply moves target B onto another square
while A stays attacked; the rook's ply-4 edge then points to B. The later A
edges form a same-target sub-run, so the whole cycle does not isolate
same-target continuity from a compliant response sequence. Both fixtures
have only two occurrences of their repeated position. Neither classifies
WXF move nature, establishes a final WXF repetition result, or adjudicates an
outcome. Imported or incomplete histories still fail closed rather than
receiving guessed identities.

The declarative policy surface is presently small: `repetition_limit`,
`repetition_policy` (`draw` or `continuous_check_loss`), and automatic
adjudications triggered at a ply with a single supported continuation policy
(`threshold_actor_continuous_check`) and `NO_CONTEST` outcome. Generic terminal
precedence is fixed in Core: no-legal-move result, continuous-check rule,
repetition draw, automatic adjudication, then max-ply. There are no declarative
check/chase/exchange/block/offer classifiers, cycle-pattern matcher, exception
precedence table, or piece-role selectors for WXF outcomes. Thus a repeated
position can currently become a generic draw from counts without proving the
WXF move classes that would determine its rule-specific outcome.

## Article 19: evidence that must be derived per move or across a cycle

| WXF clauses | Recomputable facts needed | Exceptions / pattern policy | Current support and smallest falsifiable pair |
|---|---|---|---|
| 19.1–19.2: check; kill/mating threat | Before/after positions, actor/action, whether the resulting position attacks the opposing King, and whether a legal continuation threatens mate. | A mating threat may precede check or arise from a sequence; it is not equivalent to `gave_check`. | Only `gave_check` is recorded. Hold the position/action fixed and remove the threat's supporting line or escape restriction: check may remain while the mating-threat fact changes. |
| 19.3–19.7: chase, exchange, block, offer, idle | Move-level attack/capture reachability and target identity; traded pieces; whether a route is denied; whether the moved piece is capturable; idle is the residual class after the other classes are tested. | A blocker cannot itself threaten to capture the blocked piece. These labels may overlap until adjudication priority is applied. | Generic replay traces expose identity-aware pressure and counterfactual legal-capture edges, including Xiangqi same-type targets at one square. WXF move-nature classification is still absent. A future paired probe can add/remove one interposed piece or test whether a blocker can legally take its target. |
| 19.8–19.10: perpetual check, kill, chase | Repetition-cycle boundaries and actor sequence; per-move classes; for chase, continuity of the *same* target across replies and whether replies flee or counter. | Perpetual check also applies to block/exchange/offer under 19.8; perpetual chase requires repeated attacks on the same piece, not merely the same type or square. | Public 9×10 transition test verifies a legal unilateral repeated-check cycle loses under the generic policy. A paired legal Xiangqi diagnostic repetition test confirms identity-aware capture edges retain the same target in a control and distinguish a same-type target substitution onto the same square in a second cycle. This resolves only the raw identity-observation question for these fixtures; WXF move-nature, reply-response classification and outcome remain absent. |
| 19.11–19.12: resolve and cross actions | The preceding threat, current legal reply, whether it removes that threat, and whether it simultaneously creates a corresponding threat against the opponent. | Resolution and cross-check/counter-kill/counter-chase are distinct from merely giving check or making an unrelated threat. | No threat-resolution relation is stored. Compare a checking move that escapes the prior check with a checking move that leaves the prior threat intact. |
| 19.13–19.15: protected piece; real/fake root | Attacker/protector/target identity, legal capture relation, and whether the protector can immediately capture the piece that took the protected piece. | “Protected” depends on a legal recapture; real versus fake root is determined by the immediate recapture test, not geometric defense alone. | Complete replay provides ephemeral identities, but imported roots have no persistent piece IDs and no root fact/classifier exists. Keep the protected piece fixed and add a legal protector recapture; the root classification must flip. |
| 19.16–19.19: alternating and two-to-one patterns | Ordered per-ply nature classes, actor, target-piece identity and any counter-threat on each reply. | Alternating check/chase/idle/mating patterns and one-to-one/two-to-two chase are not interchangeable with one-sided perpetual sequences. | No generic pattern language. Keep repeated positions fixed and change only one reply from idle to cross-check (or change one target identity); adjudication classification must change. |

### Bounded fixture audit for Articles 19.10 and 20.3

Article 19.10 requires a response relation, not just repeated geometric or
legal-capture pressure: after each chase, the opponent must move the attacked
piece away or resolve that chase with another piece. The chaser must then
continue attacking the *same piece* move after move. The four-ply control's
rook/target-A sequence has the required per-edge target response in this
fixture, including the first move's response to the rook already attacking
in the repeated starting position. It remains a short pattern probe, not an
adjudicated WXF result. In the eight-ply substitution fixture, ply 3 moves B
to (3,5) while A, threatened on ply 2 at (3,4), remains there. B neither
moves the attacked piece away nor blocks/resolves that attack. The token
change at ply 4 is therefore an identity-aware capture-edge observation,
not evidence for a compliant alternative perpetual-chase sequence; later
edges again target A. Do not use this fixture as the contrasting WXF case.

Article 20.3 makes perpetual chase of one opposing piece a loss for the
chasing side, but permits chasing a Pawn that has not crossed the river. It
also prohibits two or more friendly pieces perpetually chasing one opposing
piece, with an exception when one of those chasers is a King or Pawn. These
role/region conditions are part of the rule, not optional score-like
corrections. The existing fixtures do not exercise these exceptions. They
also return to the starting position only once (repetition count 2), so they
are not evidence that a terminal repetition threshold or an Article 20
outcome has been reached.

The current declarative surface has a repetition limit and only `draw` or
`continuous_check_loss`; it has no cycle-local target-token predicate,
per-chase reply/resolution relation, or role/region exception expression.
The opt-in, game-name-independent
`trace_latest_repeated_cycle_capture_facts` now selects the interval between
the previous and current occurrence of the final position, then returns its
ply-ordered identity-aware legal-capture facts. It requires exact full-history
replay and an entirely verified capture trace; incomplete or unsupported
histories return `unknown` with no partial cycle. The paired Xiangqi fixture
tests boundaries `(0, 4]` and `(0, 8]`, source/target tokens and ply order, plus
an incomplete-history negative case. It is not called by normal transitions,
terminal handling, or evaluation.

Still missing is the semantic relation needed to tell whether each intervening
reply moved the attacked target or otherwise resolved that specific chase,
plus rule-set-declared target/chaser role and region predicates for exceptions.
A future policy can declare cycle and exception conditions only after those
facts are made sound; these capture edges alone must not label a move as WXF
chase or assign a result. The present substitution fixture remains insufficient
for a WXF outcome test, so this order adds no adjudication failure test.

## Article 20: outcome policy and exceptions

| WXF clauses | Rule-set policy that would need declaration | Current gap / minimum counterexample |
|---|---|---|
| 20.1–20.2 | Outcome and precedence for unilateral versus simultaneous perpetual check, plus the enumerated draw patterns (perpetual mating threat; alternating check with mating threat, chase, idle or capture-after-check; alternating chase with capture-after-check). | The unilateral 20.1 branch is exercised through the public 9×10 Xiangqi diagnostic path. A separate generic rectangular fixture exercises mutual-check fallback to repetition draw, but deliberately omits own-anchor safety and is not a legal Xiangqi/WXF position. No 20.2 pattern declarations exist. A legal Diagram 4 reproduction remains open. |
| 20.3–20.5 | Target/chaser multiplicity, exceptions involving a friendly King/Pawn, the un-crossed enemy Pawn exception, and two-to-one chase policy. | No typed group counts or exception precedence. Hold the cycle fixed while changing one target Pawn's river status or adding/removing the second chaser; distinguish loss, permitted chase and draw cases. |
| 20.6–20.7 | Real/fake-root outcomes; Horse/Cannon versus protected Chariot; same-type chase; exact pinned-line/file/rank cases; unimpeded Horse versus blocked Horse. | No root, same-type, pin-line or blocked-Horse predicates. Paired boards differing only in immediate recapture, type equality, pin geometry or Horse-leg blockage must expose each branch. Do not collapse the pin cases into one generic boolean without the WXF distinction. |
| 20.8–20.10 | Chase-over-exchange classification precedence; special King/Pawn chaser draw exceptions; enumerated perpetual block/offer/exchange/capture-after-check draws. | No move-class overlap resolver or role-set policy. Make one repeated move both chase and exchange, then remove only the chase relation; separately change only the chaser's declared role to test the draw exception. |

### Official example anchors

Chapter 5 (printed pp. 41–50) supplies concrete sequence examples that
constrain the falsifiers. Example 1, “Perpetual checks by one player” (Diagrams
1–3), is paired with Example 2, “Simultaneous perpetual cross-checks” (Diagram
4); Example 3 is “Two-to-one Check” (Diagram 5). Example 5, “Resolving mating
threat with counter-mating threat,” is illustrated by Diagram 10. Example 7,
“Alternate Check and Chase or Alternating many checks and chase,” includes
Diagrams 12–13. Example 8, “Alternate Chase and Idle, Alternate Check and
Threat to capture material after check/discovered check,” includes Diagrams
14–16; Example 9 covers alternate chase and threat to capture after check
(Diagram 17). Example 10, “Cannon perpetually chasing Chariot,” uses Diagrams
18–22 to distinguish protected/root relations, counter-chase, multiplicity,
and idle replies. These official examples constrain the proposed paired tests;
they are not an exhaustive adjudication oracle, and their board sequences must
be read with the Articles' exceptions and move definitions.

## Fail-closed and search-identity requirements

An unknown or unreconstructible WXF move class must not be treated as `idle`,
as a generic draw, or as permission to continue. Full-history replay is
authoritative only when it verifies from the ruleset's initial state through
the current `GameState`; a custom/imported root or incomplete prefix cannot
prove a past chase target, root relation or alternation. Existing automatic
adjudication already raises `IncompleteAdjudicationHistoryError` when its
configured threshold is reached without complete history. A future WXF policy
needs an equivalent explicit unknown/incomplete path rather than falling
through to the default repetition draw.

History context is also part of search identity. Today
`generic_chess/core/identity.py::_history_adjudication_context` is empty except for
`continuous_check_loss`, where it summarizes the repeated key, occurrence
count and actors' check counts; `search_state_identity` includes that context
with repetition counts. A chase policy must add a canonical, collision-safe
context for the exact relevant cycle, per-ply classes, target identities and
policy-relevant role relations. Otherwise identical current boards and
repetition counts reached through different WXF chase histories could share an
invalid transposition result. `terminal.py`, the semantic terminal path and
`terminal_from_search_runtime` must agree on the same policy precedence and
fail-closed behavior.

These are WXF outcome rules, not facts that should be hard-coded into a
game-name branch. The generic layer should derive observable facts from
authoritative positions, legal actions and replayable history; a future
ruleset policy can select cycle predicates, type/role sets, exceptions,
precedence and outcomes. Current `PieceType` exposes anchor/promotable traits,
not the WXF-referenced King/Pawn/Chariot/Horse/Cannon roles, and no policy
surface should assume those labels are universal.

## Smallest executable slice to try first

Do not build a full Article 19/20 adjudicator yet. The first slice is now
tested: with `repetition_limit=3` and
`repetition_policy="continuous_check_loss"`, a legal public 9×10 unilateral
check cycle returns `PERPETUAL_CHECK` with the checker losing. The mutual-check
policy branch returns generic repetition draw only in a separate synthetic
rectangular fixture that omits own-anchor safety; that fixture is explicitly
not legal Xiangqi and does not reproduce official Diagram 4. A legal public
reproduction of Diagram 4 remains unverified. Target-aware capture edges and
ephemeral token identity are already available as generic diagnostic facts;
the missing piece is WXF-specific cycle classification and outcome policy. Do
not infer it from Shogi's continuous-check policy or add a generic primitive
before a paired cycle test shows the existing facts are insufficient.

## Limits of this observation

This is a source-to-architecture mapping, not an adjudication implementation or
an independent WXF tournament-result oracle. The 39 Fairy-Stockfish
perft-1 move-set checks validate only sampled ordinary legal-action sets; they
say nothing about Articles 19–20 classifications. Clock, touch-move, arbiter
procedure and tournament administration remain outside this rules-history
scope.
