# Prospective guarded royal source-only route

2026-10-05. Start from the exact board and globally conserved stock of the
previous checked-drop witness, without rerunning that producer. One new route:
owner0 P@e2, P e2-e3-e4-e5-e6, quiet promote e6-e7=TP, TP e7-e8xe9 capturing
the designated enemy R. Keep ownKe1/Pa4, enemyKi9 and all hands. Every source
origin remains P; capture transfers original R to owner0 hand.

This is an explicitly source-only VIRTUAL continuation with passive opponents
and fixed royals. Use canonical SemanticEngine.apply for eight physical events,
including real current-position own_anchor_safe and drop postconditions. It
switches side normally; restore side_to_move=0 explicitly BETWEEN virtual own
steps. Do not fabricate a GameState/history, skip an official turn silently,
claim official alternating-game legality, mate/WDL, or repetition qualification.
Preserve raw post-apply side1 and next virtual side0 positions separately.

At each prescribed step record complete current semantic legal actions and
require one matching full source/target/promotion action. The apply method
rechecks the same full action set; count BOTH enumerations against5000 and
128-per-node, no private unchecked effect shortcut. Check royal safety after
every event and global base inventory before/after. Only the initial root can
be checked; all child positions must leave owner0 safe. All promotion/capture/
hand/occupancy identities and current masks must be actual, not assumed.

Eight events max;128 physical-event budget,5000 enumerated actions,15sec TOTAL
compile/qualification. No public GameState transition/independent goal query.
Preserve any failure and stop, no route or budget replacement. Success proves
one FULL compatible guarded virtual witness, not a population transfer bound
or robustness to a real opponent. This directly executes memo Main.
