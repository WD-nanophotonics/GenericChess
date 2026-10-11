# Task003: reusable TT evidence after an aborted iteration

DEV_AUX owns this separate independent question; product stays pinned b4108a68.
Task002 establishes that successful children can belong to an aborted iteration.
They must not automatically be called wasted. Does actual retained TT work
survive, receive later probes, and preserve the returned finite-depth score?

Predeclare four existing exposed Chess roots (middle,tactic,promotion,ep),
material-only frozen tables, root tactical scanOFF, q0/hard0, ordering/TTON.
At D2, cancel after64successful formal pushes tagged to iteration2; an unreached
trigger is reported, never replaced. Max4096nodes,10seconds/call. Then run an
uncancelled warm D2 search with that same player and a cold D2 search with a new
player under identical limits. Repeat the three-call sequence in reverse
warm/cold order, with a fresh interrupted player each order. Total24calls,
120second fuse; short count-only checks while primary active. No wall benchmark.

Observe TT stores/probes independently by original keys in memory; report only
counts, depth/bound/iteration summaries and score/action/PV outputs, no raw
history keys. Distinguish entries written in aborted iteration from earlier
completed stores; count actual warm probe matches to retained entries.
Exact scores at completedD2 must match; changed ties/PV alone imply no gain.
Unreached/capped cells and absent retained entries remain negative evidence.
This is a finite reuse observation, not universal TT correctness or speed proof.
If full-depth score differs, preserve both outputs and isolate one witness
without extending the declared batch. No product changes or history truncation.
