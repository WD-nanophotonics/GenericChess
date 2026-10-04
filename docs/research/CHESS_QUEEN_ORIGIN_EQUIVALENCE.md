# Queen-origin equivalence under the current F24F contract

2026-10-04. Source-derived argument, no new transitions, prices or goal labels.
Specific to current Western rules and valid full history, not FIDE history or
a universal statement about the generic engine.

Consider valid positions differing only in one tracked own Queen: native
baseQ/currentQ/unpromoted versus baseP/currentQ/promoted. Other current board,
hands(empty), auxiliary rights/en-passant, side and absolute ply agree. Histories
correspond under the relabel and are complete/consistent with repetition counts.
Stock/graveyard constraints must independently admit each state; the relabel
does not establish reachability or a common observational reference population.

## Active rule/effect argument

Candidate/pseudo-attack source dispatch uses owner/current type. Compiled Queen
board patterns sem_08_q_quiet and sem_09_q_capture use rays, promotion_mode none
and no state guards. Quiet moves preserve the piece; captures remove an enemy
from game then move it. Origin changes no geometry, destination or anchor safety.
The emitted legacy_067 Queen drop is disabled by all-false Western drop masks;
hands remain empty under active captures.

Other active guards also do not distinguish these Queens. Pawn double-step
base predicates concern a current Pawn SOURCE. En-passant victims require
baseP AND promoted=no: native Q fails baseP, P-origin Q fails promoted=no.
Castling predicates require native unpromoted K/R, or any-type/any-promotion
occupancy at a fixed square; both Queen origins give the same result. Attacks
and anchor safety use current dispatch. Rights-clearing triggers are piece
leaves/removed-square events with no Queen-origin selector. Current Queen
capture uses remove_from_game, not base-valued capture-to-hand. If removed,
the current-board variants coalesce. Ordinary choices/actions therefore
preserve the matched relation until removal, under a corresponding policy.

## Identity/history boundary

semantic_position_key includes base/current/promoted, so raw keys differ.
Never erase provenance in Core keys or search caches. F24F has repetition
limit100000, total max_ply1000, stalemate draw and no no-progress rule, automatic
adjudication or declarations. Complete consistent history has each occurrence
count<=ply+1<=1001 before/at the endpoint: repetition is unreachable. Mate/
stalemate depend on current legal/attack state; absolute-ply endpoint is shared.
Origin-sensitive raw identity consequently gives no different goal outcome
within this contract. Inconsistent imported histories, changed rules, other
promoted families or external FIDE repetition need separate qualification.

Bounded paired controls support the source premises; original numerical rows
were lost after an interface error. MODE_EQUIVALENCE_RESULTS.md states that
evidence limitation. This derivation does not fabricate persisted raw results.

## Construction implication

Equivalent behaviour permits tying native/P-origin Queen deployment weights
without a mandatory mixture estimator in this scope. Different reference means
3/68 and1/12 compare different contexts/action competition, not an intrinsic
origin premium. Interpreting a common Q observational average still requires
an independently selected population/mixture. Approximate predictor usefulness
remains an empirical question. Shogi captured-base custody prevents extending
this Queen argument by geometry alone. No Core identity or rules changed.
