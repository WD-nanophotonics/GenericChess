# Public-transition goal interval probe

Base bbeb56a935e78f14d31b72b6c3a39ac84e9ce1ab. Current segment started
2026-10-04T06:45:35Z. Qualify cheap sound goal-label acquisition, not a new
material formula or population performance estimate. Freeze this before runs.

Implement a small bounded observer using public GameState, terminal_result,
iter_legal_actions and apply_action, with NO evaluator, material table, TT,
history reset, quiescence, type-price lookup or native search score. Goal is
owner-zero W/D/L in [-1,1] under the declared executable contract. Exact terminal
winners map to +/-1, ordinary draws0. No-contest has no W/D/L interpretation;
leave unknown. An explicitly censored terminal leaves [-1,1], not zero.
Any such censoring targets a separately declared compatible continuation;
it does not prove official full-game values under arbitrary changed rules.
Reject stale cached terminal state rather than infer labels from an override.

Each ongoing depth frontier and unexpanded action has full interval [-1,1].
Max/min combines lower/upper bounds. An exhausted action iterator establishes
complete coverage; interruption requires an extra unknown child even if it
happens on the last yielded action. A max node with a proven +1 or min node
with -1 may stop without scanning others, because the goal range bounds them.
Ongoing empty legal sets fail explicitly. Full GameState is propagated with
history/counters; no position-only cache is introduced. Report node visits,
public materializations, unknown leaves, cutoffs and elapsed seconds. Time cap
is cooperative; one uninterruptible public transition may overshoot, reported
honestly. Budget interruption retains sound intervals, not complete labels.

CONTROL roots are existing frozen Chess initial/mate/terminal evidence, not
new material validation contexts: initial state depth1, immediate-mate root
FEN from CHESS_ROOT_TERMINAL_LABELS.md depth1; one terminal checkmate and one
terminal stalemate child from its existing public action set depth0. Each
ongoing search <=64 materializations, five seconds after rules construction;
record construction separately. These bounds test the new interval contract,
not prior mate-distance/search-choice findings or relative prices.

Correctness controls use exact tiny acyclic abstract games with both owners,
terminal draws/wins, censored/no-contest leaves, empty ongoing actions, stale
status, depth/node/time interruption and action-order changes. Compare every
small budget's interval against a separate complete minimax oracle. No larger
corpus, fixed-inventory service labels, Shogi adjudication change, Xiangqi
material reference, human value, fitted coefficient or extra worker is allowed.
