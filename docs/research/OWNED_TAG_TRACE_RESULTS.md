# Ordered owned-tag controls, 2026-10-04

OWNED_TAG_TRACE_PROTOCOL.md SHA256
875dff4dbcaf5cb81a75148851d44267d8cf995be3ca49f473b502f8f3eadeeb
was frozen before adapter-control execution. All ten specified controls passed,
both actor owners for each fixture, within0.157 seconds/250 enumerated choices/
10 public transitions (caps10 seconds/512 total,128 per root/10 transitions).
Raw public action IDs, boards, hands, histories, exact tag mass and input hashes:
data/owned_tag_trace_20261004.json.

| Actual public effect | Tracked consequence |
| --- | --- |
| King-side castle | Secondary Rook follows h1-f1 / h8-f8, mass1 |
| En passant | Off-target enemy Pawn loses this owner's service, lost mass1 |
| Shogi P promotion | Same tag/base P on new square/current TP, mass1 |
| Shogi G drop with2held G | Hidden-tag mass1/2 on board,1/2 still held |
| Shogi capture of enemy TP | Tag's ownership ends, even as base P joins capturer hand |

Research-only scripts/owned_tag_trace.py reads a caller-verified exact semantic
binding and ordered effects using pinned private reference resolvers. It never
substitutes its own transition for authoritative public apply_action. Full board
and both hands agree with each authoritative child; histories advance1->2.
Tag probability sums to1, retains owner/base support or absorbing loss, and
does not use Piece equality to search for a persistent physical identity.
Three new independent controls cover duplicate equal board tokens, promotion,
anonymous hand split, generic same-owner hand conversion versus enemy loss,
unpaired/multi-count drops, binding mismatch, unsupported creation, incorrect
projection and invalid mass/support. Synthetic resolver controls do not establish
new legal-game coverage; the frozen public controls do that for their fixtures.

This qualifies a small trace mechanism for the tested effects. Private helpers
are implementation-coupled and would need hash/version qualification on change.
It does not claim all custom rules, historical reachability or all runtime
pattern populations, nor support arbitrary token creation or multi-count drops.
Session endpoints/claims, pass and unresolved outcomes need separate treatment
in any estimator; the trace must not turn RESTART into an ordinary survivor row.

## Next construction gate

No P or material coefficient was estimated. Finite-service arithmetic and these
trace controls permit a meaningful next question: choose a predeclared context
law, condition on complete current mode, and compare true two-cycle continuation
with the refreshed-mode approximation under the SAME bounded law. Avoid a spent
all-quiet population, initial-only modes lacking hands/promotions, or a single-
enemy population that exhausts all ordinary victims after the first capture.
The latter makes repeated refreshed reward a replenishment assumption rather
than actual surviving service; it can be identified before any numerical batch.

Keep actual initial inventory or explicitly identify a synthetic subset context;
do not call a sparse Shogi board missing its other physical tokens a reachable
standard-game sample. Promote/drop interventions and actor/type selection must
be declared before sampling, with coverage and original caps. A new formula
can be approximate without universal WDL calibration, but its law cannot be
changed after seeing coefficients or goal labels. Scientific objective remains
OPEN; this segment advances beyond the original memo to a new construction gate.
