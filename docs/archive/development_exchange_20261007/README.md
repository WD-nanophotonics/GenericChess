# Native half hanging-risk development evidence

Optional Standard-Chess pilot; production/search/table defaults are unchanged.
The old untuned half pseudo hanging-risk law is implemented with native bitboards:
material+4*(nonroyalCoverageWhite-nonroyalCoverageBlack)
+(hangingBlack-hangingWhite)/2, symmetric integer truncation.
Kings defend/attack but are not discounted. Pins, illegal King captures, EP
victims off the target square and exchange chains remain approximation limits.

All36prospectively fixed cells complete:4W1L7Uactivity,1W11Lclassical,
11L1Ufullstrengthreference. Unfinished is not draw. All4201played+144prefix
plies replay through Core with legal sets, rights/EP, PV and full final state.
37Core/old semantic exposed-piece controls and144native mirror/turn checks pass.
28other native objects are reused unchanged; native build2.068461seconds.
No fitting, Elo, unexposed validation, exact safety or default-promotion claim.

Eight exposed actual roots:6same,2finite worse versus activity. This diagnostic
briefly overlapped the old repeated-table trace; it is not isolated cost evidence.
Retained bad root changes g6g5 to c6c5 at1/4sec. Equal full-history child references
report g6g5 mate-16 versus c6c5 cp-866; finite analysis, not all-defense safety.
Source audit preserves the disclosed PieceValue/variant evaluation-price coupling.

raw.zip retains all declared games, replay, static, trace and diagnostic evidence.
sources.zip retains qualified/new producers, native evaluation and patch, pinned
upstream evaluation/license and shared adapter/serializer/config/suite. Recover
its exchange-20261007 directory under .local_agent in the pinned checkout; input
raw/source packages from the preceding royal/classical studies and the documented
native build/runtime are also required. This is an evidence/source package, not
a self-contained engine installer. The retained binary SHA is in the JSON index.

The rejected fresh-FEN history import and subsequent full-history correction are
preserved. A packaging-only tuple-path error is recorded with original source/ZIP
hashes; corrected final source ZIP and unchanged raw ZIP are independently verified.
Project paths are normalized in portable build/failure reports. Private local
runtime, Slack account data and credentials are excluded. Public push remains held.

Index: ../../research/data/chess_exchange_20261007.json. index.json binds every
ZIP entry and portable summary SHA. Detailed immutable evidence stays here;
LOCAL_MAINLINE.md and CHESS_DEVELOPMENT.md retain only current conclusions.
