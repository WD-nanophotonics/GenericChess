# Prospective complete target-aware Pawn distance closure

Changed question: obtain exact remaining distance mass rather than a sufficient
promotion/rank bound. The same249984 (source,target,own-blocker) worlds and full
P-origin N/B/R/Q promotion closure apply. QualifiedWesternPawnPrefix retains
double moves and the previously proved single-source EP invariant; do not edit
the old projection or old third evidence. Native initial sources include dead
ranks per the declared virtual law. Royal/turn/history omissions stay explicit.

Pawn quiet/capture masks differ, so target-free BFS is INVALID. For each blocker
and target build a reverse graph of (current source profile,square). Quiet
landings/paths may not hit target/blocker. Seed distance1 at actual admitted
capture states with clear blocker paths; reverse quiet edges add1. Absorbing
capture needs any live compiled promotion result, not arbitrary current relabeling.
Read native initial P distances for every other source; unreachable stays zero
mass and does not disappear from denominator. Preserve every blocker slab.

Same128 patterns/5000 canonical candidates/15sec TOTAL compile/census cap.
0 physical/virtual materializations, external queries or human labels. Compare
old exact1/2/3 and permanent zero support. Independent Pawn forward/double/
capture/promotion coordinate qualification precedes exact coefficient use;
completed partial output cannot be retried as if unobserved. No budget increase.
