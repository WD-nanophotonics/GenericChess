# Full conserved-stock capture with shared affine hands

New integration question: after a genuine legal opening capture, can exact
board-current/hand-base inventory rows preserve all seven unknown held prices
and certify a complete one-ply choice without choosing a scalar hand law?
This is a static reference collector on the production Core runtime, not an
interval replacement for scalar alpha-beta and not a strength experiment.

Freeze initial Standard Shogi root and four unpromoted pawn actions by board
index:19->28,55->46,28->37,46->37. At each step require a unique authoritative
legal action, full conserved ledger and nonterminal local status. No labels
selected the sequence. After these four actions enumerate ALL root actions
once, push each once, record exact affine inventory row and pop. Keep complete
canonical identities; do not filter captures, replies, declarations or ties.
Abort on terminal children rather than assigning approximate goal values.

Board coefficients: same frozen geometric_half/TR normalized thirteen modes,
same100000 integer quantization. Seven shared hand coefficients P/L/N/S/G/B/R
lie independently in[0,100000]; this is a declared uncertainty domain, NOT a
value law. Rows are owner0-oriented, exact integer constant plus signed held
counts. Board current and held base remain distinct; custody is conserved.
For each candidate, exact box minimum of its affine difference against every
other row certifies strict dominance when positive. A nonpositive bound is
inconclusive; no corner heuristic, coefficient tuning or fallback selection.

This follows the same full-stock integration budget, cumulative with the
earlier initial depth1 control:30 prior pushes,2005 conservative prior
candidate/list charge and0.094 prior seconds. Total128 attempted pushes,
5000 charged candidates/returned actions,15sec. One NEW compilation whose
initial validation probe is conservatively charged492 before instrumentation;
reuse saved initial state (no second initial_state probe). All other semantic
candidate/list/push events instrumented BEFORE execution. On failure retain
partial evidence, no follow-up widening/reset. No independent source queries,
human prices/holdouts, new context law, goal labels or worker. Restore runtime
and monkeypatches even on failure. Numeric separation must hold for all38
ordinary resources and the whole coefficient box before evaluation.
