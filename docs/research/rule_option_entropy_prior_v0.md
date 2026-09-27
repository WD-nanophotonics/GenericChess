# Static rule-option entropy prior v0

Status: frozen diagnostic hypothesis; no human material references have been
read. This is analysis-only code, not a production evaluator, material table,
or claim about best play.

## Experimental selection

Label: `CAUSAL_DIAGNOSTIC`.

The single unknown is whether executable RuleSet semantics plus a general
decision-theoretic principle can produce a game-name-independent static
material prior. The minimal observation is a per-piece Western Chess component
ledger, followed by the exact unchanged formula on Standard Shogi as a
retention control. Complete games are unnecessary: the tested mapping is from
one-step executable legal choices to a scalar, not playing strength or
long-horizon strategy.

## Frozen formula

For a piece state, let `n(s)` be the number of distinct immediate legal move
choices for that piece in snapshot `s`, keyed by source, destination, promotion
choice, and actor type (duplicate declarative patterns are collapsed). Define
the snapshot choice measure as
`h(s) = log2(1 + n(s))` bits. The `+1` makes an empty action set zero bits. The
logarithm follows from the maximum-entropy distribution over `n` available
choices: if choices have no justified preference, uniform choice entropy is
`log2(n)`. The action-count coefficient is exactly one because each distinct
successor action is one choice; no fitted or game-specific coefficient is
used.

The board-mode score is the equal mean over the two owner orientations and all
non-anchor source squares. For each source square, average the empty snapshot
and the mean of sparse one-extra-piece snapshots equally. The extra piece is
the focal piece's own current type, placed on every unoccupied square found on
its compiled movement paths, with both owner assignments equally represented.
This makes occupancy, blocking, and capture availability directly observable
without assuming an empirical board-density distribution. It is a deliberately
limited perturbation ensemble, not a model of typical game positions.

For a type with an executable hand/drop mode, compute `h` for a one-token hand
snapshot for each owner and average those owner values. The final score is the
equal mean of board-mode and hand-mode entropy. Equal mode weighting is the
maximum-entropy choice over the rule-declared custody modes in the absence of
frequency evidence; it is fixed before comparison. Types without a drop mode
use the board-mode score alone. Anchors are excluded: their capture has
terminal utility and cannot be represented as a finite ordinary material
quantity by this one-step choice model.

The per-piece ledger also reports owner-specific, empty/occupied, quiet,
capture, and promotion action components. Those component counts are
diagnostic decompositions of `n(s)`, not extra additive score terms, so capture
or promotion actions are not double-counted. Directionality, restricted
regions, and state transitions enter through the executable action set and
the equal owner/source-square ensemble. Capture disposition and declared
conditional auxiliary slots are listed separately for audit.

## Explicit limits / no-weight conditions

The sparse ensemble does not claim a realistic occupancy prior, tactical
exchange value, future mobility value, or long-horizon promotion probability.
It does not assign independent numerical bonuses for capture disposition,
promotion potential, reachability beyond immediate action options, or
history-dependent state. Chess auxiliary slots (including castling rights and
the en-passant target) are left at their RuleSet initial/default values and
are reported with guarded/effect pattern IDs; the ensemble does not vary them
across move histories. Castling actions themselves cannot enter a non-anchor
actor's move count, and an en-passant target has no history-created value in
these snapshots. This is a known limitation, not a claim that those rules have
zero strategic value. Shogi drops are sampled directly; capture-to-hand is
also reported from semantic effects. Any omitted term remains unresolved
unless a universal, independently justified model is stated before
human-value inspection.

The score is intentionally allowed to fail a later frozen agreement gate.
Human values are validation evidence only: they may not alter this formula,
its weights, or the snapshot ensemble. Xiangqi human material values are not
part of this work order. No full games, Arena, self-play, Heavy job, ABP
benchmark, or production evaluator change is authorized here.
