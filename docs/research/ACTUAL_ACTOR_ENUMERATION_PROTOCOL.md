# Unchanged-inventory actual-actor enumeration: frozen feasibility check

Base: 659ae23a0bfc3eed1cec2a802fc31d0f6f98aeb1, with the local exact
ACTUAL_ACTOR_POPULATION_PROTOCOL.md bridge. This is NOT a coefficient batch.

Use exactly the two physical_board arrays already frozen in
data/nonterminal_physical_support_20261003.json (SHA256
801cb8ca48817d4c411eed74e106e76f9cc93b3452234f26b54e20b8874148fc).
The recorded physical boards contain the actual Pawn placeholder; use them
directly, with NO substituted type, board edit or new draw. Require owner/base/
current type counts identical to compiled actual initial inventory, empty hands,
owner 0 to move, no checks and a nonterminal synthetic-history root. No
reachability or representative-population claim. Each game's reference is a
point mass on this fixed context, useful only for implementation feasibility.

Mark EVERY existing owner-0 ordinary board actor by its occupied source. Enumerate
root legal actions once and group by their actual source. Ignore anchor actions;
no hand actors exist. For each eligible first action exhaust all legal replies,
using the unchanged secured-exchange binary task, baseline custody and terminal
win=1/draw=0/loss=0. A no-contest result or empty nonterminal reply set rejects
coverage. Promotion branches belong to the same root actor. An actor with no
legal first action gets zero task success, not a game-draw label.

For each current type, report actual count n_t, successful actor count S_t and
marked-actor mean S_t/n_t. Check sum_t n_t*(S_t/n_t)=sum_i X_i exactly. Preserve
all grouped first actions, reply counts and first refutations. Do not normalize
these point-mass observations or install them as material values. The point
mass gives no inventory transfer, typical frequency or strategic validation.

Gate: exactly two roots, one process, 20,000 materializations and 30 seconds
total including compilation/validation. No early break after success/refutation,
type-specific rejection, larger budget, resampling or repair after a failed gate.
Keep failures explicit; no partial result certifies all-actor coverage. Record
protocol/program/input hashes and exact actor evidence. This check changes the
decision of whether complete actual-actor enumeration is feasible on the two
existing legal physical fixtures, not whether a physical population is useful.
