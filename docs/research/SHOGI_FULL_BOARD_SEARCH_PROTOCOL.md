# Full-stock board-only production preflight

New question: can a research evaluator with the full conserved ordinary stock
run through the existing production search without removing origin/custody
checks or choosing an unqualified hand price? Root is the standard initial
state selected by the rules, before any labels, not an outcome-selected puzzle.
One frozen geometric_half board vector, normalized by TR, uses the existing
SCALE100000 quantizer. No coefficient fitting or new duration law.

FullBoardInventory requires all13 ordinary current modes, the existing exact
global Shogi resource ledger and empty hands. Capture/held states fail closed;
do not silently substitute a midpoint, zero or the old unit hand premium.
This is an explicit restricted evaluation interface, not full-game admission.
Royal/terminal/history rules remain owned by production search and fresh Core.

One depth1/qdepth0 production search from the initial state, TT/ordering/root
tactical disabled; cap128 runtime pushes,5000 candidate+returned-action
enumerations and15 seconds including compilation/preflight. No new public
transition, independent-goal query, full support construction or depth2 reset.
Count each attempted runtime push before execution and every pop. Persist
partial evidence; stop at first failure and do not rerun this root with larger
caps. Before/after source pins, full-state runtime preservation and exact root
score0 are checks. Initial one-ply ordinary quiet moves preserve each owner's
inventory and have no promotion: all leaf scores must remain0. A tie is expected
and establishes no strength or material ordering. Save actual selected action,
statistics, evaluation calls and charged enumeration cost.
