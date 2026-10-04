# Owned-token modes and hidden hand identity, 2026-10-04

This qualifies the finite surrogate's arithmetic and specifies physical
tracking, not an implemented full game-to-P estimator. No fresh empirical
contexts, external labels or human values were observed. Source inspection:
generic_chess/core/pieces.py, position.py and semantic_executor.py; compiled
Chess/Shogi effect shapes were enumerated, not their legal-state populations.

## What the public state can and cannot identify

Piece stores owner, base_type_id, current_type_id and promoted, but no persistent
physical UUID. Two same-type board pieces may compare equal. A move's source and
ordered effects establish which entity moved; searching the child for an equal
Piece is not identity evidence. Promotion replaces current type while preserving
base/owner. Castling includes a second Rook move, so the public actor source alone
does not track every affected resource. En passant removes an off-target victim;
the destination alone does not establish which token lost ownership.

Hands stores aggregate counts by base type. If n own same-base tokens are held,
a public drop decrements n and places one, without specifying which hidden
physical instance. A chosen hidden tag therefore needs an explicit extension:
uniformly choose among those n fungible instances. Conditional on tag mass q
still held, dropped tag mass is q/n and held mass q(1-1/n). This is a declared
exchangeable identity convention, not a private ID recovered from the engine.
Dropping d such tokens without additions gives total dropped tag probability
d/n; no heuristic assignment to the first dropped piece is justified.

New same-base captures joining a hand change the next denominator. An opponent
drop cannot return a tag whose ownership was already lost: ownership loss is
absorbing for this owner's service, even though the physical token continues
in the other hand. A generic remove/place pattern need not conserve physical
identity; require a proved paired hand-drop contract or mark it unsupported.

## Ordered trace requirements before an adapter

1. Read the exact verified semantic binding and ordered effect operands, resolved
against the pre-action state as in the reference executor. Do not infer a trace
solely from board differences or a visible source/target pair.
2. move/shift carries the tag at its resolved source to resolved destination.
remove handles the resolved victim, including off-target capture; if it is the
tag, standard enemy removal ends this owner's service. An unqualified self-
remove/capture-to-own-hand variant must not use that standard shortcut.
3. A paired own remove_from_hand(count1)+place with the same base uses the
exchangeable split above. A count>1, unmatched place, arbitrary token creation
or unfamiliar ownership conversion is unsupported until specified.
4. set_current_type and public promotion preserve tag location/base; read the
actual resulting current mode. Aux effects can affect future context/legal moves
and remain in the authoritative state/history even when they do not move a tag.
5. Compare trace projection with the public authoritative child. All hand/board
counts, base/current identities and ownership must agree. Use fresh terminal
status and Session claim semantics; RESTART is not a sampled ordinary successor.

A researcher may inspect private binding/resolution helpers as implementation
evidence; they are not yet a stable public tracking adapter. Python object
identity would be brittle across serialization/promotion and is not adopted.
The existing exposure control's unique R/N mapping is a qualified special case,
not coverage for anonymous hands, compound effects or all generic rules.

Compiled shape inventory: Chess25 patterns include6 move-only,7 remove/move,
1 move/token,2 off-target remove/move/token,4 compound castle/right and5 legacy
hand remove/place patterns. Shogi155 patterns include71 move-only,71 remove/move
and13 hand remove/place. Some legacy drop patterns are disabled by masks/state
guards; a syntactic entry is not a reachable mode/action. These counts identify
adapter branches, not a claim that all patterns generate legal standard play.

## Exact finite arithmetic and independent controls

scripts/finite_owned_service.py checks explicit nonempty complete mode rows and
columns, exact nonnegative rewards and substochastic probabilities. H is restricted
to0..2, the currently qualified algebraic horizon. It computes v_(h+1)=g+Pv_h;
there is no simulation, label access, estimator, infinite inverse or positive
offset. Missing modes/float approximations/invalid mass fail closed.

Five tests pass. Independent next-mode/absorbing-branch enumeration verifies
every two-mode kernel whose probabilities are0,1/2,1 with row sum<=1, across
three reward levels. Equal immediate reward but different survival yields
different two-cycle values; common survival preserves ties. Nonabsorbing rows
are finite at H=2. Zero g yields zero regardless of P. A held mode with g=0 can
gain positive second-cycle service via an explicit transition to rewarding board
mode, without adding a premium; the numerical example is synthetic, not Shogi
estimates. Exhaustive distinguishable drop orders for n=1..6 independently
verify the anonymous-hand probability and conservation after repeated drops.

Another control constructs two hidden full contexts with the same mode: a real
successor always chooses rewarding context1, while the surrogate refresh uses
the half/half law. Coarse g+Pg gives1 versus full-context1.5. This is a concrete
closure-premise mismatch, not a failure of the polynomial arithmetic or proof
that every mode model fails. Actual-game survival/mode transitions alone cannot
certify the omitted context distribution.

## Mainline effect and immediate work

The proposal now has exact arithmetic and a defined anonymous-hand identity
convention. A later research adapter/control milestone is reported in
OWNED_TAG_TRACE_RESULTS.md. A full estimator and independently motivated context
law remain unimplemented/unqualified. Do not fill P from sparse capture existence,
set all drops to tag probability1, or call synthetic arithmetic material evidence.
The minimal frozen adapter controls cover promotion, same-type hand drop,
castling, off-target capture and ownership loss in both owner directions, within
small caps. Next specify a genuinely changed finite context/action law
and same-context closure falsifier before a coefficient batch. No need to wait
for dot or prove universal WDL calibration before these construction tasks.
