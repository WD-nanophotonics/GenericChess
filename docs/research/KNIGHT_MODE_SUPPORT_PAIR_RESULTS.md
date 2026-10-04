# Actual matched Knight source-mode/support result

2026-10-05. Frozen KNIGHT_MODE_SUPPORT_PAIR_PROTOCOL.md;
raw data: data/knight_mode_support_pair_20261005.json. Source bases remain N;
Kings/target/other Pawn/supporting Rook unchanged between the two roots.
Own K a1,R a7; enemy K i7,P e6/f7; target is physical f7 Pawn.

|Source mode|Root choices|First enemy replies|Final leaves|Strategy/task value|
|---|---:|---:|---:|---|
|Board native N e5|31|6|44|[1,1]|
|Held native N1|85|5|35|[1,1]|

Board strategy e5-f7 without promotion, then own King a1-b1 completes target
removal on the first own move; source remains owned through all final replies.
Held strategy drop g5, then g5-f7 without promotion completes on the second
own move. The g5 drop avoids the OTHER Pawn e6's forward capture at e5 and
threatens f7. Rook a7 pins f7 to King i7 while enemy chooses its first reply.

Both complete public/binding action identities, exact public/binding capture
rewards, source/target traces, full real history and fresh ongoing terminals
match. Budget103/128 shared transitions,1850/5000 public/binding enumerations,
0.359 seconds including compilation. All10 source pins unchanged. Missing34
stock remains explicit synthetic scope; no earlier completed path was rerun.
Every adversary branch succeeds, so binary upper1 certifies global VALUE1;
no canonical action tie, full strategic solver or material vector is claimed.

## Same-geometry no-Rook values: rule derivations, not extra observations

Board source alone still has value1: capture f7 first, choose King a1-b1 on
the next own turn. Enemy King starts three files from source f7, cannot reach
it in two moves; the remaining Pawn stays on file e and cannot capture it.
No-Rook root/continuation has legal quiet King replies and safe own King move.
This is a source-derived strategy/range proof, not a new sample.

Held source alone has value0. First King moves leave the source held until
its last action, which cannot drop and capture. If the first Knight drop
threatens f7, its square is e5 or g5; enemy f7-f6 is legal without the Rook
and escapes both jump geometries. Other Knight drops permit a safe enemy
King move, keeping target f7 beyond source's next capture geometry: King i7
has five neighbors, Knight attacks at most two and occupies at most one,
and neither enemy Pawn nor far own King blocks the remaining empty choices.
Promotion occurs after native capture movement. These exhaust first actions.

The source-absent empty/R-only task is0 by the SAME designated-source event.
Thus the scoped coalition tables are:

|Mode|F(empty)|F(N)|F(R)|F(N,R)|Allocation N/R|
|---|---:|---:|---:|---:|---|
|Board N|0|1|0|1|1 / 0|
|Held N|0|0|0|1|1/2 / 1/2|

Only F(N,R)=1 in both rows is empirically certified here. The other entries
are rule arguments. Allocation1/2 is from the specified mathematical convention,
not another observed game value. Rook's attributed influence changes with
source deployment mode although its own mode/geometry and joint success stay
unchanged. This is NEW attribution information absent from joint success or
actor-tag completion alone, but transport to one static R coefficient needs
an independently declared context/role law and separate use evidence.

Do not fit coefficients from this exposed table, infer a natural Shogi hand
price, average its two deliberately matched states as a population estimate,
or multiply hidden completion/survival marginals. Prospective full role-law
cost and unsupported modes remain in ROLE_BALANCED_PIN_LAW_DESIGN.md.
