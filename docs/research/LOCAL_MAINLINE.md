# Current local research mainline

This file contains the changing scientific route for the one local Agent. `AGENTS.md` and the latest user instruction take precedence. The former Chat work-order status and request-specific directions are archived in `docs/archive/courier_worker_20260928/CURRENT_MAINLINE.md`; they are not active policy.

## Objective

Build a cheap, scientifically justified, game-independent rule-derived material prior for chess-like games. Generic executable RuleSet semantics must cover the material-relevant legal moves, captures, occupancy and blocking, regions, promotion, capture-to-hand, and drops needed by Chess, Standard Shogi, and Xiangqi. Do not extend full historical adjudication merely to postpone material research. Validate any missing semantic primitive with its smallest direct test.

Study static Chess values first, retain Standard Shogi as a control, then evaluate a frozen formula on Xiangqi as a holdout. Human material values are scarce validation evidence, not training targets. Do not fit coefficients, piece exceptions, or choose among formulas for human-value agreement. If a formula fails, diagnose which general rule consequence it misrepresents and state a new independent scientific argument before changing it. Distinguish statistical mean value from context-dependent value; a static scalar is a zeroth-order approximation.

The old rule-only scalar and AMTU candidates failed their declared checks. A context-indexed simulation partial order is a valid structural result, but it does not itself yield a context-independent cardinal value. Rule semantics alone have not established a unique transition measure or aggregation across contexts. Avoid rerunning kernel, entropy, identity, or feature-enumeration probes without a new principle that can change a concrete decision. This negative result does not prove that all scientifically grounded approximate priors are impossible.

The bounded Shapley diagnostic in `SHAPLEY_CONTEXT_DIAGNOSTIC.md` examined marginal minimax payoff allocation as a game-independent valuation principle. A two-resource, two-context exact finite game reverses the allocation; the rules and Shapley axioms do not select context weights or a conventional material unit. The subsequent `ADVERSARIAL_CONTEXT_INTERVAL_DIAGNOSTIC.md` uses a single initial-reachable finite graph and an explicit removal map. Its exact marginal interval for A is the full `[-2,2]` W/D/L-difference range while B's is `[0,0]`, with no pointwise type dominance. The executable check in `PIECE_REMOVAL_INTERVENTION_CONTRACT.md` rejects legal capture as a context-preserving deletion: Chess discards the victim but changes attacker, turn and history; Shogi also transfers the token to the capturer's hand. A real-game `R_t` therefore needs an explicit model choice, and the finite interval remains conditional. The finite `SEARCH_LEAF_DECISION_LOSS_DIAGNOSTIC.md` shows that exact root decision regret can demand opposite type rankings at different cutoff depths even with one initial root. The code audit in `SEARCH_DEPLOYMENT_CONTRACT_AUDIT.md` finds no single fixed leaf contract in current use: UI Python alpha-beta iterates under node/time limits and evaluates during quiescence, while native semantic search has an explicit depth and no quiescence. F156 confirms shallow Python/native parity with quiescence off using an indexed control profile. `CHESS_QSEARCH_BOUNDARY_PROBE.md` isolates the Python quiescence setting on F156's frozen Chess root: the depth-2 selected action changes, with equal reported score and no independent exact outcome label. `CHESS_ROOT_TERMINAL_LABELS.md` certifies another frozen Chess root by Python/native legal transitions: 2 immediate wins, 19 immediate draws, and 10 ongoing actions with unknown eventual outcomes. These are deployment and validation assumptions, not rule consequences. Keep context-specific/ordinal results and do not repeat existing recapture, hand persistence, simulation, F156 parity, or the tied qsearch witness. `CHESS_MATE_ROOT_QSEARCH_GATE.md` shows the labelled mate root exits at `root_immediate_win` before quiescence for both limits, so it cannot compare quiescence policy. The subsequent mate-in-two and material-changing roots below supersede that old next-root lead. Retain native no-quiescence as a control, Shogi as a retention control, and Xiangqi material values as a holdout. Do not start large self-play, Arena, or teacher fitting by default.

`CHESS_MATE2_QSEARCH_CERTIFICATE.md` now gives a non-shortcut Chess root: six actions force mate within three plies, fourteen immediately draw, and thirteen remain unresolved at that bound. Python depth-2 quiescence-on selects a certified short mate; quiescence-off and native no-quiescence select Kd1e2. A separate capped exact proof establishes that Kd1e2 also forces mate, within five plies, with the line checked by native transitions. Both selected actions win. Their lines preserve identical material inventory, so this witness measures mate-distance/search-boundary sensitivity and cannot identify relative material values. Do not search more invariant-inventory tactical roots as a material-prior proxy. A future material-prior decision-loss comparison must involve legal material-changing alternatives and independently certified outcomes; first re-examine whether such labels can test a static rule-derived prior without adding a chosen context distribution. Keep Xiangqi values sealed.

`CHESS_MATERIAL_CHANGE_OUTCOME_BOUNDARY.md` tests that requirement directly on one pawn-augmented Chess root. The q0 Python/native choice captures the pawn, while q4 chooses a shorter forced mate; independent bounded proofs show both selected actions force a win. Material change alone therefore does not distinguish their terminal W/D/L, and mate distance is another declared objective rather than a rule-given material unit. Do not extend this family of king-rook mate fixtures to search for a coefficient. The next scientific step is to state a game-independent comparison objective and context-selection principle that could identify a static prior, then seek the smallest material-changing falsifier for that declared principle. Keep Xiangqi material values sealed.

`CHESS_PAWN_VALUE_ABLATION.md` shows the positive pawn control value causally affects the depth-2 no-quiescence choice on that root: setting only `P` from 4 to 0 changes capture to a quiet king move, while qsearch still selects the same short mate. A separate capped proof shows the quiet ablation choice also forces mate within five plies, as does the original capture. This establishes evaluator decision sensitivity with no W/D/L quality distinction; the profile remains arbitrary. Do not tune `P` from this witness. The outstanding issue remains an independently justified comparison objective and context selection, not another local coefficient sweep.

`ROOT_DECISION_IDENTIFIABILITY.md` tests the strongest simple root-regret contract directly: a single declared initial root, fixed cutoff, and exact Win/Loss labels. Zero regret admits an open set of material ratios, and pure material decisions are invariant under common positive rescaling. This route can validate a frozen prior but cannot derive its cardinal unit. That result prompted the resource-conversion check below. Do not infer a rate from the mate fixtures or from Xiangqi holdout values.

`RESOURCE_CONVERSION_UNIT_CHECK.md` rejects cost-free resource conversion as a cardinal-unit derivation. Existing public/semantic capture fixtures show Chess and Xiangqi remove victims, while Shogi demotes a captured promoted pawn into the capturer's hand. Promotion and capture also change location, custody, turn, and future options. Inventory deltas are exact bookkeeping, but no rule says the before and after states have equal utility. Next seek an independently motivated loss and normalization for a dimensionless structural approximation, or another source of cardinal scale; predeclare contexts and falsifiers before another formula. Do not reuse entropy or feature counts as valuation by default.

Semantic scope check: `build_xiangqi_diagnostic_ruleset()` covers ordinary single-ply movement and capture, including palace and river restrictions, horse-leg and elephant-eye blocking, cannon screens, soldier crossing, facing generals, and own-anchor safety. Its module explicitly excludes full historical adjudication and its compiled IR is not native executable because of square-zone guards. All 17 cases in `tests/test_xiangqi_diagnostic_semantics.py` passed on 2026-09-29; the older `test_xiangqi_static_setup_fixture.py` is intentionally geometry-only and must not be mistaken for the executable diagnostic RuleSet. This inspection uses rules, not Xiangqi material values. Before claiming completion, test the exact semantics used by the eventual prior on all three games and report the Xiangqi diagnostic scope as a limitation; full adjudication is not a reason to defer material research.

`XIANGQI_SCREEN_EVENT_MEASURE.md` now isolates the compiled cannon `path_count_eq=1` guard. A two-square screen is an exact disjoint union of occupancy cubes under the existing V2C finite-population measure; the focused illustrative four-token population gives probabilities `1/6, 2/3, 1/6` for zero, one, two screens. Conjoining an enemy target gives `4/15` in a separate five-token fixture. The 24 non-anchor horse-leg/elephant-eye exact occupancy guards are owner-relative one-square empty events; the one typed opponent-General guard belongs to an anchor-only action and correctly fails the three-label helper. Compiled owner-relative zone guards reproduce General palace and Elephant river boundaries in focused tests. A compiled central-source cannon capture event computes exact V2C probability `2426/85173`, independently matched by a hypergeometric expression and by the new local physical-event composer. This establishes path-count, cube-intersection, blocker, zone, and type-preserving action-event primitives; the broader ledger still needs transitions, held mode, and comprehensive coverage accounting. No Xiangqi material values were read.

`PROMOTION_STATIC_PREMIUM_DIAGNOSIS.md` revisits frozen V2E results without another candidate run: Chess pawn raw capability rose from 1.4923 to 3.1275 solely through `T(P)=1.6352`, halving all nonpawn/pawn ratios and failing the frozen Chess gates. Shogi pairwise ordering also missed its gate. The general defect is treating a conditional, future promotion option as a standing type-local premium under an assumed event measure; this does not make V2D a pass. V2D's Bishop/Pawn ratio remains high at 4.188; the existing exchange-survivability witness demonstrates a missing reply consequence but cannot correct that ratio without a context measure. Do not tune V2E after the gate or expose Xiangqi values.

`INITIAL_CONTEXT_COVERAGE_CHECK.md` tests the uniquely rule-declared initial position as a comparison context. Western Chess has 20 legal initial actions: 16 pawn and 4 knight; bishop, rook, and queen have none. The initial context therefore cannot, by immediate option counts alone, identify a static value for three of five ordinary types. Later contexts need a declared horizon and weighting. This closes the initial-only context route without rerunning an entropy formula. The earlier exchange-survivability witness likewise establishes a real omitted reply but supplies no context weight or quantitative correction for V2D's Bishop/Pawn residual. The remaining question is a defensible comparison and relative-value construction for a cheap approximate prior.

`MATERIAL_SCALE_CONVENTION.md` resolves a narrower issue: for a pure material evaluator, positive common rescaling leaves decisions unchanged. Reporting a nonnegative raw vector divided by its positive maximum ordinary-type value is a cheap, label-invariant per-RuleSet gauge, not a valuation formula or fit. This removes the demand that rules uniquely provide an absolute score unit; it does not identify relative values, context weights, or the embedding scale against nonmaterial engine terms. The live scientific problem is therefore an independently justified *relative* prior and comparison context. Do not use gauge choice to rescue a failed ratio gate.

The bounded Shogi extension in `INITIAL_CONTEXT_COVERAGE_CHECK.md` enumerated 900 two-ply histories under a 1,200-history/15-second gate. Bishop and knight actions appear by then, but no promoted type or hand mode appears. Full type coverage through uniform reachable histories therefore needs a deeper and potentially much larger ensemble; this does not justify treating histories as strategic visitation. The next useful question is a predeclared, representation-invariant context weighting and relative-value objective with a tiny falsifier, rather than another unconstrained reachability expansion.

Existing exact preference labels have limited coverage for that objective. `ADR-057-independent-exact-preference-corpus-r5.md` reports 12 effective roots, all from anchor movement or capture/recapture families. `ADR-065-natural-terminal-reference-corpus-r10.md` reports seven clean V12 roots: five anchor/check, one capture/recapture, and none for drop/hand or promotion. A sampled R5 capture witness is DRAW against a LOSS alternative, so it supplies a real root preference, but these sparse synthetic labels do not define a broad relative-value context measure. Reuse them as bounded falsifiers of a separately frozen prior, not as a new fitting target or reason to regenerate the same unsuccessful corpus.

`R5_CAPTURE_LOSS_MATERIAL_CONTROL.md` now establishes one positive validation sensitivity that the Chess mate controls lacked: on a frozen synthetic capture-to-hand root with exact DRAW/LOSS action labels under its authoritative `max_ply=6` terminal contract, two arbitrary material-only profiles at the same depth-2, no-quiescence search contract select respectively DRAW and LOSS. The LOSS choice legally captures a `D` into hand. Depth 1 selects LOSS under both profiles. At depth 2 with qsearch limit 4, both profiles instead select DRAW, showing a concrete frontier dependence. The R5 records mark mixed max-ply dependence, so the labels are not unbounded-game outcomes. This proves that a material coefficient can alter exact outcome quality within a bounded RuleSet, while leaving the general relative vector, context weighting, and cross-game prior unidentified. The second root was selected after the first gave no W/D/L separation, so this is a targeted falsifier, not a performance estimate or tuning target. Keep the sparse corpus coverage caveat and Xiangqi holdout.

`FIRST_ACTION_TARGET_ACCESS_CHECK.md` separates two previously conflated random-target quantities. A four-vertex exact counterexample holds source-local action count and lifetime reachability fixed while changing the number of first actions with a path to a target. ADR-130's product remains a valid source diagnostic but cannot be used as first-action target access. A synthetic RuleSet test confirms that two distinct, locally valid off-target capture actions collapse to one V2D public removal row, which cannot identify either postaction destination. A second synthetic check shows V2A's successor occupancy cube omits an off-target victim condition and assigns the same raw capability as a quiet action. Boundary sources make the full off-target synthetic audit coverage incomplete and are reported as such. Neither old ledger can simply be postweighted. A new local type-preserving physical-event composer now retains distinct destinations, constrains the victim, and canonicalizes two equivalent removed-square references; an independent use objective remains before any score.

`INTRINSIC_BOARD_EVENT_COVERAGE.md` extends that composer to a bounded global ledger for all non-anchor current types: five Chess, thirteen Standard Shogi, and six Xiangqi diagnostic. All 24 board-mode type audits have zero unsupported intrinsic candidates under the explicitly local, static scope. Chess pawn's four promotion choices and Shogi pawn's optional/forced branches retain distinct resulting types; history-conditioned en passant and auxiliary state effects remain ledgered exclusions. Duplicate physical descriptions are unioned; allowed Shogi held drops, disabled Chess/Xiangqi legacy drops, and dynamic anchor-safety exclusions are reported separately. No material coefficient or human Xiangqi reference has been computed. Held mode and the independent reason to treat random-target service as material utility remain open.

`HELD_DROP_EVENT_COVERAGE.md` adds a coarse, separate hand-to-board event ledger for the seven droppable Standard Shogi base types. Compiled masks yield 144/144/126/162/162/162/162 owner-summed target options for P/L/N/S/G/B/R, with empty-target cubes and exact one-for-one hand removal and board placement effects. The promoted TP mask and Chess/Xiangqi legacy masks are disabled. Shogi pawn's nifu and drop-mate related state/postconditions, and dynamic own-anchor safety, are explicit exclusions; no hand-conditioned occupancy probability or board-to-hand value conversion has been inferred. This is semantic progress, not completion of the static material prior.

`FIRST_ACTION_SERVICE_PILOT_PROTOCOL.md` now predeclares a new structural proxy before numerical values: expected count of deduplicated physical first actions that can eventually serve a uniform requested square, with V2C source-conditioned board occupancy, directed positive-probability transition reachability, and a separate hand-conditioned Shogi mode. The protocol explicitly treats source/target uniformity and coarse occupancy as assumptions, counts promotion branches, gives capture no extra bonus, and freezes failure gates and cost limits before Chess/Shogi comparison and Xiangqi human holdout. This is a testable candidate, not yet a validated material prior or completion evidence.

`FIRST_ACTION_SERVICE_PREREFERENCE_RESULTS.md` records the published numerical implementation and frozen exact Chess/Shogi raw vectors before consulting human-value references. The SHA manifest and reproduction test lock the formula, inputs, and outputs. Both audits ran under two seconds locally. Shogi held-mode route count is much larger than board-mode, and unpromoted R exceeds promoted TR because optional promotion counts as extra first-action branches; retain those predictions for validation rather than adjusting the formula. Xiangqi human values remain sealed.

`FIRST_ACTION_SERVICE_VALIDATION.md` reports the locked post-freeze result: Chess N/P 3.7421, B/P 2.2076, and R/P 6.1245 each miss unchanged bands; Q/P passes. Standard Shogi board-mode cosine 0.9919, Spearman 0.9012, and pairwise 0.9103 pass all three retention thresholds, while the R/TR ordering is inverted locally. The combined candidate is rejected by the Chess gate. The likely general defect is treating unlimited eventual access and route multiplicity as material utility without action cost or adversarial survival; this remains a diagnosis to test, not permission to tune. Keep Xiangqi human values sealed under ADR-131's pass-before-holdout sequence; rule-only Xiangqi transfer/cost checks may proceed without opening references. Seek a new independent relative-value principle.

`FIRST_ACTION_SERVICE_COMPONENT_DIAGNOSIS.md` sharpens that failure without a new formula: frozen pilot/V2C raw ratios are exactly Chess P `306183/321404`, B `1/2`, N/R/Q `1`; all thirteen Shogi board types are `1`. The Shogi pass therefore adds no new relative differentiation beyond V2C, while the Chess color-domain penalty overshoots. This falsifies unbounded first-action route count as a sufficient general relative prior and closes this path; do not tune a distance horizon or piece factor to rescue it. The Xiangqi human holdout remains unopened.

`CHESS_ARRIVAL_PROFILE_CROSSING.md` tests the tempting finite-deadline repair without fitting a formula. On frozen positive Chess topology and uniform source-target pairs, bishop access leads knight access at one and two own moves (`39/256` versus `25/256`, then `1/2` versus `185/512`), but knight leads by three (`377/512` versus `1/2`). At unlimited moves bishop remains `1/2` and knight reaches `1`. Thus a temporal target-access scalar needs an independently justified deadline, intervening reply model, and arrival utility; topology alone does not select them. `SEARCH_DEPLOYMENT_CONTRACT_AUDIT.md` already establishes that current engine paths do not supply a universal deadline. Keep the conditional ordering and Xiangqi human values sealed.

`XIANGQI_INTRINSIC_LEGALITY_BOUNDARY.md` checks the static-event ledger against executable Xiangqi legal actions in two exact states. At the standard initial position all 43 non-anchor intrinsic actions match public legal actions. With a single Soldier screen between facing Generals, the intrinsic ledger has three Soldier moves but only one is legal: two lateral moves expose the own General. This concretely bounds what the ledger's excluded `own_anchor_safe` condition means. Local occupancy event mass is an optimistic capability, not a fully legal move probability; a subsequent score needs a declared state measure to include this safety consequence or must report the bias. No Xiangqi human reference was read.

`SHOGI_PAWN_DROP_LEGALITY_BOUNDARY.md` isolates a parallel held-mode gap. A synthetic state with one held Pawn and one same-file unpromoted Pawn has 70 coarse empty drop targets but only 64 executable legal drops; all six missing drops are on that file. Promoting the board Pawn to `TP` restores all 70 legal drops without changing the coarse mask. The result verifies the state-dependent nifu exclusion, not a hand-value premium or drop-mate model. Cross-mode valuation still needs a justified state/context measure.

The two Shogi states also have identical empty/own/enemy occupancy projections and identical hands. The V2C event measure uses those three labels and does not specify a promotion-state distribution. Their differing legal-drop sets prove that no correction based only on the old three-label occupancy input can recover nifu probability. A typed, promotion-aware state measure would be an additional assumption, not a coefficient to infer from this witness.

`CHESS_EN_PASSANT_LEDGER_BOUNDARY.md` establishes the opposite direction of local-event error. After a certified legal White Pawn double step, Black's Pawn has one intrinsic ledger action (ordinary advance) and two executable legal actions, the additional one being an en-passant capture gated by history/auxiliary state. Thus, across the three direct witnesses, static intrinsic events are neither a global upper nor a lower bound on legal actions: dynamic safety and state guards can remove events, while excluded history can add legal actions. A future prior must state both scope errors and their context dependence. These checks establish RuleSet semantics, not a relative material score.

A same-board Chess control clears only the en-passant auxiliary slot and removes that legal capture. Together with Shogi's same-three-label `P`/`TP` pair, this proves that occupancy-label models lose information required for exact action eligibility in two distinct ways: current type/promotion state and history/auxiliary state. The full RuleSets execute those conditions, but an averaged event probability requires a specified joint distribution over them.

`RULE_DERIVED_PRIOR_LITERATURE_AUDIT.md` checks primary predecessors after the first-action failure. Pell's METAGAMER derives fast fixed piece values from mobility, discounted eventual access, capturable types, and goal features across chess-like games; the published material run uses equal unit advisor weights, calls weight assignment open, and omits its planned static promotion term. Clune's abstract-game evaluator combines payoff, legal-move control, and termination but learns from randomly explored states. These are useful precedents, not an independently specified relative-value objective for this mainline. Do not adopt Pell's weights or discount from Chess resemblance, nor silently turn Clune's sampling into a rule-only prior. Keep Xiangqi human holdout sealed.

The primary Kuhlmann–Dresner–Stone 2006 general-game player derives candidate board/piece features from a formal description, but deliberately keeps maximizing/minimizing heuristics separate and selects search suggestions online rather than deriving a static weighted material vector. Its controlled evaluation chooses a feature heuristic with game knowledge. This confirms that automatic feature discovery alone does not settle the comparison and aggregation premise needed here.

`UNIFORM_ANCHOR_TARGET_EQUIVALENCE.md` proves that replacing the pilot's uniform requested square with an independent uniformly placed enemy anchor leaves the board quantity exactly unchanged: each event's hit probability is its reach-set size divided by board area. This closes a nominally goal-linked relabelling of the failed candidate before another score run. A genuine goal consequence needs a specified legal anchor context and adversarial response/terminal-progress loss, not mere contact with a uniformly sampled square.

`SHOGI_STALEMATE_SCOPE_CHECK.md` records a separate goal-linked terminal limit: the local Standard Shogi product sets noncheck no-move `stalemate_result="draw"`, while the primary Japan Shogi Association match rules do not specify that edge as a draw. This is an unverified local terminal convention, not grounds to change gameplay on ambiguous evidence. Do not use local Shogi no-move W/D/L as official ground truth if a future material objective depends on it. Current board-mode static comparisons do not depend on that adjudication.

`SHOGI_PAWN_DROP_MATE_BOUNDARY.md` verifies a more direct goal exception against the official JSA prohibition on pawn-drop mate. In two executable synthetic states, the same empty pawn-drop target is coarse-eligible and would check the enemy King. Without Gold protection the opponent has one reply and the drop is legal; with protection a hypothetical drop leaves zero replies and checkmate, so the public action is forbidden. Immediate goal proximity is therefore not generically positive even within one RuleSet: legality depends on action kind and postconditions. Do not infer a material premium from terminal threat counts alone.

A tighter Shogi action-form control reaches the exact same checkmate `Position` by a legal unpromoted board Pawn advance but forbids a held-Pawn drop to that position. Thus a goal score on resulting positions alone cannot determine move eligibility; the RuleSet postcondition must inspect the action form. This is a semantic result and supplies no relative material unit.

`REPLY_COUNT_GOAL_PROXY_BOUNDARY.md` combines the certified Chess mate/stalemate root with that Shogi action-form pair. Zero opponent replies can mean a legal win, a legal draw, or a hypothetical forbidden drop. Therefore reply count alone is not a game-independent goal objective. A successor must apply full legality and terminal status first, then independently justify how any nonterminal reply reductions across contexts become a static relative material value. Do not rerun a response-count candidate as if the zero-reply case were uniformly beneficial.

`CHESS_HISTORY_CONTEXT_MULTIPLICITY.md` checks a tempting context measure after initial-position coverage failed. Four distinct legal depth-four knight-move orders reach one identical Chess `Position`; a fifth declared history reaches another. Uniform history weighting gives the shared position 4/5 mass in this subset, while uniform distinct-position weighting gives it 1/2. Full `GameState` histories differ and this is not an exhaustive-depth distribution. History sampling is a legitimate declared policy, but its path-multiplicity weight has no rule-given strategic or material-utility interpretation. Do not use it as a hidden default context distribution for a new static score.

`EXPECTED_OUTCOME_POLICY_BOUNDARY.md` adds Abramson–Korf's primary random-continuation objective as a distinct, independently motivated policy candidate: each legal action is selected uniformly at its node, so complete histories have branch-product probabilities rather than equal mass. On an exact two-ply finite game, this expected-outcome rule chooses `A` with payoff `+1/3` while adversarial minimax chooses `B` with payoff `0` over `A`'s `-1`. This is a small assumption-sensitive falsifier, not a rejection of the paper's heuristic. It opens a testable policy-dependent comparison route but does not supply a cheap type projection, a state/context measure, or a rule-given material unit. Do not run large random playouts or regression until those components and a bounded cost/failure gate are specified; keep Xiangqi human values sealed.

A second exact finite check applies the pure optional-action monotonicity theorem: adding a losing option beside an existing Draw leaves minimax at Draw but lowers uniform-random expected payoff from `0` to `-1/2`. Therefore random continuation is not directly a strategic resource utility for an optional-action contribution; it can penalize an option that a rational chooser may ignore. This narrows, without disproving, its possible role as a heuristic or validation policy. Do not equate its expected payoff with a rule-implied positive material increment.

`R5_RANDOM_CONTINUATION_PILOT.md` is a cost-capped, seeded check of that distinct policy on the already-frozen R5 DEVELOPMENT material-control root. At 100 random legal continuations per action, four exact-DRAW actions yielded 100/100 sampled draws each, and the exact-LOSS capture yielded 98 draws and 2 losses. The result is descriptive, dominated by the RuleSet's authoritative six-ply cap, and cannot estimate a Chess/Shogi material coefficient or prove random-policy decision quality. It warns that rare adversarial losses can be diluted in a small random sample. Do not enlarge the sample or fit to this root without a specific decision-changing question and resource gate.

A direct memoized exact-random-policy follow-up on that same R5 root aborted at the predeclared 10,000-state cap before its five-second time cap; it yielded no complete expectation. Do not raise the budget and repeat without new state-compression evidence and a specific decision that exact probabilities would resolve. The sampled observation and this cost boundary keep the random-policy route conditional rather than turning it into a cheap static prior.

`R5_RANDOM_SAFE_KEY_COST_CHECK.md` tests one genuine compression argument before repeating that computation: R5's draw repetition policy permits Core's authoritative position/ply/repetition-count search identity to omit raw history. On the frozen exact-LOSS action, the same 10,000-state/five-second cap still aborts at 10,000 identities with **zero cache hits**. The first traversal prefix offers no reusable state even under the safe key, so this particular compression does not justify a larger exact run. Continue toward a cheaper, independently motivated type projection or a different bounded falsifier, not a budget increase on R5.

The R5 random-continuation pilot's 482/500 `max_ply` draws are valid under its synthetic six-ply terminal contract but are censored relative to Chess/Shogi play without that cap (96.4% of sampled lines). The exact-LOSS capture has 96 capped draws among its 100 continuations. Do not transfer its sampled mean or minimax labels to a longer-horizon random-play material objective; the pilot only diagnoses how the finite contract dilutes rare terminal events.

`CHESS_SHALLOW_INVENTORY_IDENTIFIABILITY.md` tests the next obstacle to projecting any state-level target onto cheap static Chess coefficients. Exhaustive initial-state legal histories through three plies number 1/20/400/8,902. All balances through ply two are zero; at ply three, 8,868 remain zero, 30 have Pawn balance +1, and four have Knight balance +1. Bishop, Rook, and Queen balance columns are identically zero on this support, so no weighting or outcome regression there can identify their separate material coefficients. A deeper ensemble needs both a cost gate and a context-selection principle; do not silently treat the canonical initial state as adequate training support.

`V2H_HISTORICAL_EVIDENCE_RECONCILIATION.md` closes a tempting old-candidate lead. Frozen ADR-133 V2H already passed Chess/Shogi development-reference gates; it is not an untried candidate. Its Xiangqi path stopped at global typed-event coverage and square-board implementation dependencies, without a valid unchanged-formula Xiangqi material holdout. The unsupported typed General-facing event is projected out of the non-anchor vector, but that does not satisfy the declared global coverage contract. Today's complete-candidate test also stops at a frozen V2D source-hash mismatch before reconstruction; the old freeze cannot be silently rebased. Do not repeat V2H validation or treat its applicability failure as numeric human-value disagreement. Its uniform supported-source mass remains an explicit model assumption and does not settle the context/utility problem.

The exact finite decision-loss graph now has a quiescence-extension control in `SEARCH_LEAF_DECISION_LOSS_DIAGNOSTIC.md`: extending only the forced second-ply edges after nominal depth 1 gives the same evaluated inventories and zero-regret ranking as unextended depth 2, opposite the unextended depth-1 requirement. This isolates actual frontier semantics from the named depth. It does not establish a canonical quiescence policy or type values; any search-use validation must specify its operator and resource budget.

Future work may consider a lightweight state-dependent value `V_i(s)=V_{0,i}+ΔV_i(s)` with few generic state variables. Evaluate explanatory ability and complexity together on frozen cross-game holdouts. Strong engines or expert moves may serve as validation, not flexible training targets. This is a later stage, not permission to bypass the static benchmark.

## Evidence required for mainline completion

`PHYSICAL_PLACEMENT_SAMPLING_RESULTS.md` supplies exact structural masses and
an unbiased direct Pawn-conditioned sampler; naive Shogi structural rejection
alone would need roughly 3.16 million draws. The first full-inventory common
frame in each game yielded twelve zero type-task scores in 1,642 transitions.
These two frames are not a population mean. All sixteen positive-gain actions
have a legal focal-loss reply. `EXCHANGE_TASK_BACKGROUND_DIAGNOSIS.md` also
separates global net gain from focal survival on inventory-preserving controls:
background exposure flips only the global task. A local-survival replacement
does not rescue the twelve original zeros and is not adopted.

`PHYSICAL_EXCHANGE_SUPPORT_RESULTS.md` records a separately frozen existence
test of the unchanged global task: eight Chess and five Shogi focal-R roots
all zero, 3,098 transitions in 1.422 s. Shogi exhausted 128 proposals before
its eight-frame cap, so support evidence is explicitly incomplete. No larger
rerun, fitted density or coefficient followed. An exact cell-polynomial count
on the six recorded Shogi Pawn frames finds differing dead-free L/N completion
counts; parent-fixed redraw would bias the joint conditioned law. This closes
that proposed optimisation without new score samples. The next step needs a
specific structural support argument or independently motivated strategic
population before another type-score batch; inexpensive execution alone does
not justify one. The task's cheap static additive interpretation remains open.

`CONSTRUCTED_PHYSICAL_SUPPORT_RESULTS.md` resolves the narrower support question
without enlarging random batches: one predeclared full-inventory frame per game
passes the original Pawn conditions and all-current-type common quiet screens;
focal R's legal board capture immediately checkmates. Raw resulting-position
enumeration independently confirms check plus zero replies. Chess used 130
materializations/0.094 s; Shogi used 314/0.218 s and transfers one Pawn to hand,
custody+2. These finite admitted placements prove each original conditional
R-task expectation is strictly positive, despite the earlier negative samples.
They are terminal-win witnesses, not representative frequencies, nonterminal
exchange support or piece ratios. Never mix them into a random mean or adjust
population weights toward them. Useful signal and additive material validity
remain the next scientific questions, rather than mathematical all-zero support.

`NONTERMINAL_PHYSICAL_SUPPORT_RESULTS.md` adds an exact controlled distinction:
one non-Pawn Bishop/Rook swap per complete mate frame preserves inventory and
all original screens but permits one legal King escape after the same capture.
Both capture and reply remain ongoing, with net gain+1 Chess/+2 Shogi. All
focal actions/replies plus four public replays took 465 transitions/0.312 s.
Thus positive conditional support need not exploit terminal-win scoring.
These checking-capture witnesses are not sample frequencies, quiet-capture
support or relative prices. Do not keep constructing R examples or enlarging
random support batches in place of justified strategic signal/static use.

`MOVEMENT_INCLUSION_TASK_BOUNDARY_RESULTS.md` checks a distinct semantic premise
before claiming action-set dominance for types. On one common quiet sparse
Chess frame, R coordinate actions are strictly included in Q's, but the complete
unchanged task gives R=1,Q=0: the same capture gives R an ongoing positive-gain
King reply, while Q additionally controls the escape and causes a stalemate
draw. 94 transitions/0.063 s include both public capture replays. This does not
contradict pure optional-action monotonicity: replacing a type changes mandatory
attacks, replies and terminal payoffs, so the old actions' semantics are not
preserved. Do not infer full transition/payoff dominance from coordinate-event
inclusion. The sparse frame is outside the frozen full-inventory law and is
never averaged into it. Useful approximate population validity remains open.

`EXCHANGE_ADDITIVITY_TARGET_RESULTS.md` separates the candidate's static target
before coefficient projection. On the unchanged frozen full-inventory Chess
frame, two existing Rooks each secure the SAME Pawn; joint first-turn success1,
individually successful actor count2, actual branch custody+1. Exact overlap/
disjoint finite measures have identical individual probabilities but different
union probability and marginal eligibility contribution. 219 materializations/
0.125 s preserve all original focal evidence. Expected actor count is additive
under a common joint law by linearity, without independence; joint success is
not. Adopt that identity only, not capability count as validated utility or
physical deletion value. The single-focal replacement law has not established
compatible per-piece marginals, type/source averaging or inventory transfer.
Keep this constructive target distinction when choosing a justified static
approximation and frozen predictive loss; do not generate more redundancy
fixtures or change the binary task to obtain an additive answer by definition.

`FOCAL_INVENTORY_TRANSFER_RESULTS.md` audits that transfer premise without more
scores: every non-Pawn focal query replaces an initial own Pawn and hence has
one fewer P/one more t than unchanged actual initial inventory. All ten such
Chess/Shogi base-type vectors have L1 difference2. Against any nonempty actual-
inventory reference law their full-Position supports are disjoint (TV1), so the
generic bounded-task transfer bound is trivial. This proves no actual mean
difference and no reference nonemptiness; equal Pawn counts likewise do not
prove equal measures. Preserve the explicit prototype-background assumption,
but do not claim small distribution shift from shared rules/background alone.
A task-sufficient projection or frozen predictive transfer validation needs a
separate argument before treating single-focal marginals as additive material.

`ACTUAL_ACTOR_POPULATION_RESULTS.md` constructs a replacement-free conditional
bridge: under one fixed-inventory law, mark a uniformly selected actual actor
of each type; its mean times the type count exactly reconstructs expected
successful-actor count. Source weights must come from that joint law. Five
frozen abstract contexts show uniform supported-source weighting differs, and
with variable inventory context-then-all-actor sampling differs from pooled
actor weighting. Even exact overall-mean reconstruction leaves nonzero count
prediction loss. These are measure identities, not game scores or material
validation. Adopt the construction only; the old replacement sampler is
unchanged. The actual-board feasibility check below addresses complete marking,
not the reference law. Next declare a joint reference and its source/conditioning
cost contract, then a distinct variable-inventory deployment law and frozen
count-prediction criterion. Do not fit to validation labels or
confuse capability-count loss with strategic outcome/custody/material validity.

`ACTUAL_ACTOR_ENUMERATION_RESULTS.md` completes all actual ordinary actors on
the two existing frozen physical boards without substituting or moving tokens:
15 Chess and 19 Shogi actors, 2,107 transitions/0.703 s. Both have actual initial
inventory, quiet roots and empty hands. Exact count reconstruction and public
action/transition checks pass. This establishes low-cost marking on these two
point-mass fixtures only; their R-only successes are not population type values.
Do not repeat them as new support evidence. A uniform unchanged-inventory
physical reference could provide an explicit uncertainty baseline, but its
structural/quiet conditioning and proposal costs require a separate contract.
No representative sampling, inventory-transfer or strategic-use claim follows.

`ACTUAL_INVENTORY_SAMPLING_RESULTS.md` specifies a replacement-free joint
reference as uniform unchanged-inventory physical placements conditioned on
Pawn structure, Shogi non-Pawn dead-placement exclusion and quiet ongoing
actual roots. Direct Pawn layouts use C(48,8)C(40,8) Chess factors and 57^9
Shogi file-pair factors; remaining-token uniform injections and whole-board
rejection preserve the declared conditional law. The frozen seed admitted
one Chess root after 3 proposals and one Shogi root after 14, in 0.125 s;
no task/value scores were computed. This supplies a computable synthetic
uncertainty baseline, not strategic visitation or reliable acceptance rates.
Adopt the construction/observed feasibility only. Next specify a distinct
variable-inventory deployment law, count-loss baseline and independent margin
before type estimates; fast admission is not full-reply cost or material validity.

`POST_CAPTURE_VALIDATION_CONTRACT.md` freezes a narrow independent use: predict
own board-actor capability count after one real opponent capture, stratified
equally by victim type, preserving all state changes. Compare squared count
error to zero and a reference-only constant, with a predeclared 10% improvement
margin; this is an engineering diagnostic, not material/WDL validation.
`POST_CAPTURE_SCOPE_RESULTS.md` verifies its first implementation on the two
existing admitted boards. Complete capture coverage includes all 5 Chess victim
types but only B/P/R/S in Shogi. Two selected actual children retain Chess check
and Shogi promoted attacker/held Pawn, with 50 opponent drop replies across
branches. Full GameState/public-transition checks pass; 1,988 materializations
take 0.766 s. Both scope counts are zero, not validation risk or coefficients.
Next freeze finite reference and independent all-stratum deployment generation,
seeds/counts/resource gates before values. Missing strata, zero signal/baseline
risk or incomplete coverage cannot qualify; do not tune or reuse scope fixtures.

`CAPABILITY_CORPUS_PROTOCOL.md` freezes four reference roots per game and one
independent real post-capture child per ordinary victim type, including seeds,
complete coverage, weights and generation/label cost gates before values.
`CAPABILITY_CORPUS_GENERATION_RESULTS.md` records an incomplete run: eight
unlabelled references and all five Chess strata were generated, but Shogi R
failed at 128 proposals after B/G/L/N/P succeeded; S was not attempted. Its
rejections were 109 dead non-Pawn, 17 check and 2 lacking ongoing R captures.
Only 35 capture transitions/0.265 s were used; no coefficients or validation
labels were computed, missing strata were not renormalized. This does not prove
empty R support. Preserve the failed combined gate and do not extend its budget.
Next consider an exact globally dead-free joint sampler: Pawn layouts need
W(P)-weighted mass for their constrained L/N completion counts, not parent-fixed
redraw. Derive/bound that algorithm and preserve whole-state quiet/capture
conditioning before another corpus experiment; preprocessing counts as cost.

`REVERSE_PLACEMENT_EFFICIENCY_RESULTS.md` rejects a law-correct reverse-order
proposal: exact W81/U63 counts imply only 0.5346x the original raw acceptance,
for any shared quiet/capture predicate. No failed-corpus retry was made.
`FILE_JOINT_SAMPLING_RESULTS.md` instead verifies direct joint file-polynomial
counting and integer unranking: Z=12666047573426791865632639560 restricted
physical layouts, at most 81 states/table, approximately 0.156 s with compilation.
A complete tiny-space independent oracle proves rank coverage/no duplicates;
the full 26-token draw passes inventory, nifu, non-dead and distinct-cell checks.
This removes intrinsic rejection while preserving the globally conditioned
Pawn/L/N law (old intrinsic acceptance approximately 20.43%). Full remaining
14-token assembly and quiet/capture filters are still required. Validate that
integration and freeze a new cost/corpus protocol before new batches or labels;
the previous corpus remains incomplete, not retroactively repaired.

`JOINT_ACTUAL_FRAME_RESULTS.md` subsequently validates full Shogi Q integration:
remaining 14 actual tokens are uniformly injected on 55 free cells, full
inventory/mobility drift fails closed, and unchanged check/terminal filtering
is retained. A frozen one-root construction needed two joint proposals (one
check rejection), 0.172 s including compilation/preprocessing, with no intrinsic
dead placement. Full state evidence and deterministic tests pass. Next freeze
the new complete corpus experiment before values; construction/cost success
is not capture coverage, predictive validation or a change to the failed corpus.

`JOINT_CAPABILITY_CORPUS_RESULTS.md` records a new separately frozen run with
the verified algorithm: eight reference roots/all twelve victim strata complete
in 29 capture materializations/0.297 s. Complete reference labelling then uses
14,998 materializations/4.5 s; every reference actor count and raw coefficient
is zero in both games. The predeclared nonzero-signal gate therefore fails;
deployment labels remain unread, with no risk/improvement claim. Keep complete
unlabelled deployment evidence and all reference refutations. This demonstrates
construction improvement without usable finite-pilot signal, not zero true
support (earlier positive witnesses exist). No bigger batch, new seeds or
validation-label fishing. Next needs a new scientific premise for task/reference
population usefulness; do not repeat background exposure or R-support probes.

`SAFE_REFERENCE_SUPPORT_RESULTS.md` excludes a specific proposed repair before
new sampling: condition reference Q on no legal opponent ordinary capture S,
while retaining deployment Q conditioned on an ongoing type-t capture C_t.
C_t is contained in complement S, so all deployment strata become undefined
under the same safe reference. Twelve saved public capture replays verify the
operator/event interpretation in 0.188 s; no deployment task labels are read.
Mutual-no-capture filtering also eliminates ongoing positive two-ply token
gain (terminal wins are exceptions). A separately declared cross-population
reference/deployment is possible, but needs its own scientific transfer premise;
no safety filter, formula or rescue batch is adopted. Daily dot request
GC-SLACK-20261004-100247-cbfff6a6 asks for a minimal justified alternative;
consultation is not a gate for independent research.

`DAILY_ADVISOR_REVIEW_20261004.md` records the full daily dot reply and local
decision: retain failure and same-state support qualification; defer proposed
local secured-capture service pending a distinct justified use. Existing
background/focal-survival controls already address much of that proposal.
Read-only inspection of the new reference's 63 Chess/55 Shogi capture actions
finds only 1/2 saved ongoing first-refutation focal-loss candidates; remaining
62/53 cannot prove local success because only the first global refutation, not
all physical successor identities, was retained. No new labels or independent
validation claim follows. Do not repeat old controls or rescue the candidate
with selective relabelling; specify new use/evidence prerequisites first.

`LOCAL_CAPTURE_ATTRIBUTION_RESULTS.md` then freezes and resolves the missing
complete-reply evidence on only the eight exposed replacement-free references:
63 Chess/55 Shogi capture actions reproduce saved global zeros/reply counts,
but 20/31 are fully locally secured. All replies' physical custody/terminal
labels and state hashes are retained; 4,971 transitions/1.968 s and independent
public replay tests pass. This is target separation on diagnostic data, distinct
from the twelve older substituted-focal zeros, not a rescue of old coefficients
or independent validation. Retain local tactical service only as a possible
structural diagnostic; declare its intended use/new independent predictive
contract before any coefficient batch. A global material/WDL-use bridge is
still unsupported; unrelated losses, sacrifices, delayed gain and overlap
remain limitations. Deployment labels and Xiangqi holdout stay unread.

`LOCAL_SERVICE_VALIDATION_RESULTS.md` freezes a distinct narrow use and NEW
independent corpus before coefficients: predict locally successful board-actor
count after a real capture with sum N_t v_t. Eight fresh reference roots and all
twelve fresh strata complete; nonzero reference vectors are frozen before new
deployment labels. All20 labels/replies take 15,465 transitions/5.078 s, including
3,462 Shogi opponent drops. Both games fail the unchanged double-baseline 10%
gate: Chess risk17.93 exceeds zero10; Shogi risk6.52 exceeds constant5.39.
Reject this finite inventory-transfer use despite positive local service; no
vector tuning, larger batch, material installation or holdout read. OLD global
deployment labels remain unread. Future work needs a justified state-dependent
service-to-static-material bridge, not more service batches or fitted rescues.

`SERVICE_MATERIAL_BRIDGE_RESULTS.md` closes that memo question with an explicit
conditional theorem and a goal-prediction objective: invariant conditional
type/owner service means plus independently justified positive goal/service
calibration imply an optimal static conditional-mean predictor. Neither premise
is established by count additivity or the failed finite transfer. A ten-state
exact two-context game has identical inventory/service but opposite solved goal
values, unavoidable statistic-only squared risk1; no universal bridge follows.
Affine static goal-risk compression requires declared U/D and full-rank inventory
covariance for identifiable slopes (fixed-inventory support has rank0). Reject
material promotion of current service vectors; no real-game fit or holdout read.
The outstanding theory task is closed with evidence, not a successful material
model. A future route needs its own complete-goal/measure/support/cost premises
before experimental admission; no new batch is queued by this conclusion.

`PARTIAL_GOAL_RISK_RESULTS.md` relaxes that probe's unnecessarily strong
complete-label admission gate: sound intervals for unresolved exact goal values
can certify a frozen predictor's risk margin for every completion. Exact paired
quadratic bounds pass a four-state arithmetic control with 1/4 label mass fully
unknown; all-unknown and wrong-sign controls remain inconclusive/failing.
Five tests pass. This supplies a cheaper comparison contract, not real-game
validation or a material formula; candidate, deployment and sound interval
semantics still need independent justification before any new batch. The prior
theorem also corrects individual service invariance to sufficient, not necessary:
aggregate signed residuals may cancel. Earlier finite failures and unread
holdouts remain intact; no new goal-labelled game population was generated.

`PUBLIC_GOAL_INTERVAL_RESULTS.md` advances interval acquisition on public
GameStates without material/search scores: depth1 initial Chess stays [-1,1],
an existing certified winning root becomes [1,1], and interrupted branches
retain unknown bounds. Complete tiny-game oracle checks cover depth/node/time
limits. A subsequent source audit found legal_actions omits Session declarations;
an explicit addendum includes reassessed claim choices as virtual outcome leaves.
Both-owner Shogi WIN controls are exact, RESTART stays unknown, and board
materializations are counted separately. Eight observer plus existing declaration
tests pass (41). This is label-acquisition correctness on diagnostic roots, not
a material prior/population validation. Official Shogi stalemate, restart target
and uncapped-goal semantics remain qualified limits. Next needs an independently
motivated candidate and deployment, not deeper mate or service repetitions.

`SECURED_EXCHANGE_COMMON_CONTEXT_RESULTS.md` records a frozen 15-root sparse
Chess/Shogi pilot of the new task under one equal-mass physical-context law.
All focal actions/replies completed in 1,973 materializations and 0.469 s.
Chess B/R=1/3,Q=2/3; Shogi B/R=1/3. Open diagonal/orthogonal opportunities give
conditional differentiation while the defended diagonal motif scores zero.
This validates cheap enumeration and the declared task contract, not its
population weights or material-use validity. Invalid roots fail explicitly;
broader physical-placement and type-dependent support accounting remain open.
Do not install these motif scores, tune context weights or repeat captures to
claim the static material-prior objective complete.

`SECURED_EXCHANGE_TASK_CONTRACT.md` records the first accepted Slack/dot research
consultation and a new, explicitly conditional candidate: a context average of
optimal focal-action/adversarial-reply binary token-gain success. Its exact
two-context algebra distinguishes strategic choice from route/action averages;
optional bad actions and duplicate descriptions do not lower its score. Three
fixed public legal-action witnesses confirm Chess removal +1, Shogi custody
transfer +2, and hand deployment 0, with complete opponent replies at low cost.
These establish a task contract, not type values or predictive success. A common
physical-context law, invalid-configuration accounting, the horizon and additive
material interpretation remain assumptions requiring separate evidence. The
research objective permits motivated approximation assumptions; it does not
require rules to select a unique context distribution. Do not repeat recapture
witnesses or the old failed proxies as a substitute for that remaining question.


The Agent task ends successfully only when project evidence supports the objective above: a specified, inexpensive, game-independent material-prior construction derived from executable RuleSet consequences; the material-relevant semantics it uses verified on Chess, Standard Shogi, and Xiangqi; a formula and evaluation protocol frozen before Xiangqi holdout inspection; Chess validation, Shogi control, and Xiangqi holdout results reported with failures and limitations; and relevant correctness and cost tests passing on the published result. Document the derivation, observations, and remaining limits so a reader can distinguish the rule-derived claim from deployment choices or fitted references. If the evidence instead rejects a candidate or leaves a required premise unsupported, update the scientific route and continue the same task. A completed probe, batch, scheduled turn, checkpoint, or negative result is not evidence that the mainline objective is complete.
