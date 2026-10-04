# Shogi sparse counterfactual support and hand-completion cost

2026-10-04. This is a proposed control scope and source-derived feasibility
argument, not a coefficient/goal experiment or proof of standard reachability.
Official initial inventory and capture/drop rules were checked against
[Japan Shogi Association rules](https://www.shogi.or.jp/match/taikyoku_rules/),
Articles3/5/10. Local reference: standard_shogi.py, drop_derivation.py,
resource_mode_context.py and OWNED_TOKEN_MODE_QUALIFICATION.md.

To adapt the TWO_VICTIM_CONTEXT_PROPOSAL.md geometry, on9x9 use own King a1,
enemy King i8, tracked board mode e5, two enemy native Pawns e5+v/e5-v.
Reflect ranks/swap owners. Native7 board types plus6 promoted board types
retain base provenance. For a held mode remove the tracked board piece and
place exactly one corresponding own base in hand. No native hand promotion.
Fresh histories/ply0 and standard effects; no rights/EP slots are invented.

Drop the two df=0 layouts from EVERY mode: two enemy unpromoted Pawns on the
same file violate nifu scope. The remaining10 unoriented shell layouts share
both owner directions. All board modes are away from dead terminal ranks;
enemy Pawn files are distinct. e5 cannot attack i8 under any standard ordinary
movement pattern (delta4,3), and the enemy Pawns cannot attack own King a1.
Eligibility still requires actual fresh public checks; this argument alone
is not an enumeration result. No new Shogi root/action observation has run.

There are only5 physical tokens in these board or held contexts, whereas
standard inventory is40. The35 absent tokens are explicit counterfactual
missing resources, NOT a Shogi graveyard. resource_ledger correctly rejects
this as a full-inventory state. Do not weaken that guard or rename the absent
stock as captured: standard captures preserve global base inventory. Sparse
move/trace calculations can be a separately declared model, not conservation
or official-game validation. Goal-linked Shogi stalemate remains censored;
service endpoint handling does not certify official WDL.

## Why completing the sparse board using hands exceeds the current choice cap

Every one of the7 droppable base types has missing stock: even a Pawn tag plus
two Pawn victims uses only3 of18 Pawns; every other type has at most one token
of its initial global stock. If all35 missing tokens are placed in the two
hands, at least one player has at least4 distinct held base types (pigeonhole).
Both Kings are initially unchecked. A drop cannot expose an attack on its own
King. For any held base there are at least39 legal drop destinations here:
81 squares minus at most5 occupied,18 dead-drop squares,18 same-file nifu
exclusions and1 checking Pawn square that might be drop-mate forbidden.
Subtracting all exclusions for EVERY type deliberately overcounts restrictions;
it remains a conservative lower bound. N has at most18 dead squares; only P
has nifu/uchifuzume. With at most two already-board Pawns per owner, nifu can
exclude at most18 squares. Ordinary non-P drops are not forbidden for giving
mate. These distinct base/destination choices cannot be coordinate-aliased.

That player's complete action set therefore has at least4*39=156 drops alone,
exceeding the128 choices/state cap. Assigning all missing stock to the other
hand does not solve H2: the other side's reply needs its full action set too.
This proves the HAND-ONLY completion idea incompatible with this cap and
unchanged sparse board, not that every full-inventory control is impossible.
Parking stock on board could reduce drops but changes blockers/king safety and
the context law. Choosing such a board law needs independent motivation.

## Held identity and next bounded scope

One held tag has n=1 initially but same-base new captures can increase the
denominator after an own action; preserve exchangeable q/n rather than always
assigning subsequent drops to the tag. Ownership loss is absorbing. Only a
first same-base drop can give second-own-action service; its probability under
complete-side uniform choices is D/A and its per-tag bound is1/n. Unknown
reply branches retain full mass. H2_CUSTODY_DEPLETION_BOUND.md applies to the
initial enemy pool even with custody; longer horizons cannot use that bound.

Next choose explicitly between a sparse20-mode counterfactual CONTROL pilot
(13 board +7 held, inventory limitation retained) and an independently defined
conserved-board law. Freeze one total cap and endpoint/unknown treatment before
any estimate. Do not run separate per-mode batches, complete stock in hidden
inactive hands, assign a premium, or claim this design supplies Shogi labels.
