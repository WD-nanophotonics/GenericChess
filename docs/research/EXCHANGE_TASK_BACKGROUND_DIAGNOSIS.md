# Net exchange and focal survival: distinct objectives, same full-frame zeros

The frozen background control and local-survival comparison diagnose the
full-inventory pilot without new sample selection or a changed material prior.
Their protocols were hashed before execution; raw protocol/program/input hashes
are preserved in the corresponding files under data/.

## Inventory-preserving control

For Chess and Shogi, move one background Pawn out of an opposing Rook's line
while preserving every token and the complete focal R legal-action set. The
unchanged net-custody task scores shifted=1, exposed=0. In the exposed context
the focal R's capture gains a token, then the opponent captures the other Pawn.
The focal R stays owned on its postcapture square, but global net gain becomes 0.
Four roots required 765 enumeration plus six replay transitions (771 total),
about 0.266 s under a 2000-transition/10-second cap.

This is exact background liability sensitivity. It is not an error if the target
is global net gain; it would be a misleading label if called focal survivability.
The original task is retained without changing its formula.

## Paired-task diagnostic on identical successors

A separately motivated local tactical-service task asks for an immediate gain
and focal token survival through every opponent reply, with terminal win/draw/
loss handled as in the original task. It deliberately omits other-token losses.
This is an experimental diagnostic in Chess/Shogi board scope, not a generic
piece-price derivation, hand conversion or proposed replacement engine profile.

Reuse the same twelve frozen full-inventory roots plus the four controls.
Enumerate successors once and score both tasks. No new seed, population, source,
inventory, weight, horizon, pruning or human reference. All original actions,
reply counts and zero net scores reproduce. 2,407 materializations completed in
about 0.797 s in the recorded run, below the 30-second/20k cap.

| Population | Net-custody score | Local-survival score |
| --- | --- | --- |
| All twelve frozen full-inventory focal roots | 0 | 0 |
| Shifted background controls, both games | 1 | 1 |
| Exposed background controls, both games | 0 | 1 |

All sixteen positive-gain actions in the full-inventory data have at least one
legal reply that loses the focal token. Across those actions there are also 186
replies where the focal token survives but net gain fails due to other liabilities.
These counts distinguish existence of several causes from the first refutation
encountered. The initial 13-versus-3 first-refutation diagnosis must not be used
as evidence that background tax alone explains the twelve zeros.

## Research decision

Reject the proposed background-only explanation of this frozen pilot's zeros.
The local task demonstrates the intended distinction in the controls but does
not rescue full-inventory informativeness. Do not adopt it simply to avoid a
negative result, nor increase samples or tune a sparse density for favourable
ratios. One frame per game cannot reject either population expectation.

The subsequent frozen support check found no positive R root in eight Chess
and five Shogi frames; Shogi exhausted its 128-proposal cap. This is negative
and partly incomplete support evidence, not proof of a zero population mean.
See PHYSICAL_EXCHANGE_SUPPORT_RESULTS.md for counts and the exact conditioning
check that rejects a biased non-Pawn-redraw shortcut. Preserve
both objectives and discuss their intended interpretation at the next substantive
advisor window; independent work is not contingent on a reply. Xiangqi values
remain sealed and installed engine evaluation is unchanged.
