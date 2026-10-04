# Resource-preserving, origin-refined mode contexts

2026-10-04. Prospective construction, not an empirical coefficient law or a
reachable-play claim. This changes the old focal Pawn replacement and empty-hand
initial-inventory scope. No old scored/exposed boards are reused.

## Mode and resource accounting

Use board/base/current and hand/base, with fixed tracked owner. Native Chess
Q/Q and promoted P/Q are different modes; aggregation requires an independently
declared origin mixture. Chess capture removes a base-origin token, so remaining
board base counts per owner plus an explicit graveyard equal initial counts.
Shogi capture transfers custody and demotes, so board base counts PLUS BOTH hands
equal initial GLOBAL base counts. Per-owner Shogi conservation would be false.
Anchors remain one per owner, never in hands or graveyard. Piece current/base/
promoted consistency must be checked independently of these count equations.

An inventory equation is necessary, not reachability: synthetically putting an
original own Pawn into own hand has no supplied capture/re-capture history.
FEN alone cannot infer whether a Chess Queen originated from a Pawn. Preserve
declared origin fields rather than reconstructing them from the current type.

## Proposed conditional reference law

For each selected owned mode, start with the compiled physical initial list.
Choose one own base token uniformly from the requested base group and mark it;
set ONLY its declared board promotion or move it into own hand. Never replace
its base with another family. Other tokens keep initial base/current/owner.
All ordinary resources remain accounted for; no victim replenishment occurs
within actual continuations. This deliberately narrow synthetic law omits
other tokens' promotions/custody changes and is not mode-complete game support.

Place remaining unpromoted Pawns uniformly under their rank/file constraints.
Chess: labelled Pawns uniformly without replacement among ranks1..6. Shogi:
choose distinct files uniformly for each owner's remaining unpromoted Pawns,
then ranks uniformly from owner0 0..7 / owner1 1..8, rejecting shared occupied
squares. Promoted/held marked Pawns free an unpromoted Pawn file. Place all
other board tokens, including a promoted marked Pawn and anchors, uniformly
without replacement on the remaining squares. Whole-proposal rejection checks
dead board modes, nifu, both anchors unchecked and ongoing synthetic roots.
Retain every rejection, not only successful contexts or capture actions.

Labelled sequential placement has constant duplicate-token multiplicities;
the mark makes its own identity distinct. Conditioning is explicit and varies
by mode. No uniform strategic visitation or common-context coupling is claimed.
Chess rights/en-passant are empty; ply0 and a single synthetic initial history
record are declared. Later transitions preserve the actual child history.

Complete canonical PublicGame choices, including Session claims, define a
prospective uniform action policy. Promotion alternatives remain distinct.
Actions by other own entities are allowed: a tag may idle. Complete local
enumeration must fit existing caps; an exceeded cap is unsupported, never a
truncated renormalized action law. A root-only feasibility check does not
establish affordable four-ply paths or a positive service vector.

## Smallest next gates

First implement count/origin/tag guards and check transformations independently:
Chess promoted Pawn leaves Pawn base count unchanged; native Queen replacement
is rejected; Shogi capture-to-hand changes owner but not global base inventory;
held tags and unsupported promoted hand IDs must be distinguished.

Then freeze six-stratum ROOT feasibility separately: Chess board P/P, P/Q, Q/Q;
Shogi board P/P, P/TP, hand/P. New seeds, one admitted root per stratum, shared
at most128 proposals per game and conservative15s/5000 enumeration accounting;
128 choices/root remains an incomplete-on-excess gate, not an acceptance
filter. Freeze exact proposal allocation, hashes and endpoint handling before
observation. This is a feasibility pilot, not mode coverage or coefficient
sampling. No pilot is authorized by this design alone.

If feasible, separately freeze the H2 closure experiment. Actual second-cycle
reward versus frozen reference-mode reward is the target. Death/terminal stops
future service, not current earned reward. Refined modes absent from reference
support are unsupported rather than zero. Sampling a new reference until the
answer looks favourable or filling absent modes with epsilons is prohibited.
Independent deployment usefulness remains a further gate.
