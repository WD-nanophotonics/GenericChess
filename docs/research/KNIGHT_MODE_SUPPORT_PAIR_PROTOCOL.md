# Frozen matched Knight mode/support comparison

2026-10-05. New question: does source deployment timing change the supporting
Rook's contribution under the SAME geometry and designated target? Two roots:
own King a1, own native R a7, enemy King i7, enemy native Pawns e6/f7. Source
is own native N e5 OR one held native N; owner0 turn, fresh history/ply0.
Target is physical enemy Pawn f7 in both cases. Missing34 stock is explicit.

Freeze strategies before observation: board N first e5-f7 WITHOUT promotion,
then own King a1-b1; held N first drop g5, then that N g5-f7 WITHOUT promotion.
Exhaust ALL enemy replies after BOTH own actions. Verify designated capture
by source and source still owned at every final leaf. Earlier captured-target
completion is historical; do not require live enemy target on the second turn.

The g5 drop is specified for geometry, not selected after evidence: e5 would
allow the OTHER Pawn e6-e5 to capture the source, whereas g5 threatens f7
without occupying either Pawn's forward file. R a7 pins target f7 to King i7.
This is a source-derived prediction before observing either new root.

One SHARED budget for both cases:128 public transitions,5000 public/binding
enumerations,128 choices/state,15 seconds including compilation. Frozen case
order board then held. Preflight destination, save all action lists/leaf traces,
real history, terminal checks and source hashes. Any cap/scope failure retains
[0,1] for unresolved strategy/value; no retry or per-case budget reset.

No previously completed root/path is rerun: earlier board-N controls had King
i8 and no Rook; earlier pin controls used Pawn source/Rook a6/King i6. Here
task, mode contrast and King/Rook geometry differ explicitly. No coefficients,
human labels, background resampling or favorable followup drop substitution.
Same-geometry no-Rook contrasts may be source-derived afterward, not falsely
advertised as empirically measured coalition values.
