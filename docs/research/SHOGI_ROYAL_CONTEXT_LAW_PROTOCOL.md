# Prospective royal interposition law

Declared before the new population observation. This is a synthetic mechanism
law, not an opening-reachable population, game strategy or independent use test.
Keep the two already declared shared deadline laws, without fitting.

Uniform72 contexts: file f=0..8 and own-King rank r=0..7. Owner0 K is (f,r),
enemy R is (f,8), enemy K is (8,8) for f<=4, otherwise (0,8). Own native P is
((f+5)%9,3), own hand has P1; enemy hand has P16,L4,N4,S4,G4,B2,R1.
This restores global stock40. Owner0 moves and is checked; the previous mover
must be safe. Missing opening history is not manufactured.

The conditional task samples a held-P drop, then moves only that physical
source until capturing the original R. All other pieces stay passive, including
royals. Own turn is explicitly restored between virtual events. No alternating
GameState, adversarial opponent, repetition claim, source table or WDL query.

Before execution predict63 coarse drops in every context (empty, live-rank and
nifu filters). Legal drops are exactly (f,j), r<j<8, count7-r. Keep the full
semantic action list including King escapes. King counts: r0 interior4/edge2;
r1..6 interior6/edge3; r7 interior5/edge3. Total613 complete action entries.
No new successors: one complete position-level enumeration per context, max128
per root,5000 entries total,15sec total cooperative cap. Preserve failures;
never rerun the producer or increase caps. Save every position/list, guards,
stock and input hashes. This does not certify historical public terminal states.

Straight forward source routes from each legal drop to R take exactly8-j board
events: promote at entry to rank6 when needed, then Gold's forward step. Each
prefix interposes the R until capture; the distant enemy King cannot attack it.
Pawn drop never checks that King, so pawn-drop mate is inapplicable. This family
argument is analytic; the separately frozen eight-event route is empirical.
Lower bound: P/TP vertical displacement <=1 per event. Total service time9-j
includes the drop; apply shared moment m(9-j), not a product of averaged moments.

Uniform legal-set resampling gives V(r)=sum[j=r+1..7]m(9-j)/(7-r), r<=6.
At r7 retain failure reward0 and population mass1/8; do not renormalize it away.
Fixed coarse attempt gives F(r)=(7-r)V(r)/63, illegal attempt reward0.
Population legal mean=sum[r=0..6]V(r)/8; fixed mean=sum[j=1..7]j*m(9-j)/504.
These are different policies on the SAME declared contexts. Their difference
is initial selection/reweighting, not an estimate of omitted opponent loss or
an automatic correction to the earlier royal-free prototype.
