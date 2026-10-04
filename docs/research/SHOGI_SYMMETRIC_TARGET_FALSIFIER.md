# Symmetric Pawn-target law fails native file-only support

2026-10-04. Source-derived decision,0 new observations. The proposed Shogi
adaptation in SHOGI_SPARSE_LAW_SUPPORT.md excludes df=0 in all modes to avoid
two enemy unpromoted Pawns on the same file. Therefore neither initial victim
is on the tracked e-file. Both native Shogi Pawn and Lance preserve their
file under every own move. Both enemy Pawns likewise preserve their files.

Before the second own action, no enemy hand replenishment can place a new
ordinary token on the e-file: initial enemy hand is empty, and an enemy reply
capturing one of our tokens keeps it in hand until a separate later drop.
Own tag loss is absorbing. Thus tagged native board P or L cannot remove ANY
ordinary enemy victim within actual H2 on this entire10-layout support.
Promotion cannot rescue it: from centre e5, a first noncapture Pawn step ends
e6 outside the promotion zone; a Lance can reach promotion zone but still
cannot capture an off-file victim on that first move, then promoted Lance may
capture on second own action. Consequently the blanket L H2 zero claim would
be FALSE: voluntary promotion on an empty ray changes its future movement.

Correct conclusion: native P H2 is provably0, while native L H1 is0 but H2
needs promotion-qualified analysis. This distinction is why current mode,
base provenance and actual transitions cannot be omitted. With initial P e5,
two own moves at most reach e7; promotion on the SECOND action occurs after
its vertical capture geometry has been applied and earns no off-file removal.
The Pawn H2 positivity gate alone rejects this specific symmetric Shogi law
as a complete positive native-board construction. It does not reject sparse
controls, Shogi drops or lifetime service generally. No failed-law batch ran.

A changed mechanism question uses distinct target roles, one straight-front
(0,1) and one leap-offset(1,2), common to every tested type. Different files
avoid nifu without removing the file-only target. This change follows a
structural support defect, not exposed WDL or desired piece-price sorting.
The next frozen small control will check real custody, promotion branches and
held n=1/n=2 identity, not estimate a new all-type vector or resurrect old
safe-capture/net-inventory predictors.
