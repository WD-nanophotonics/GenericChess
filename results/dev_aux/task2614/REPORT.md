# DEV_AUX2614 — fixed-foe evaluation cost scan

Status: COMPLETE_COST_ONLY; science OPEN. Attempt 1 failed before search because
direct execution lacked the repository root on sys.path. Its zero-search
failure and original script are preserved in attempt-1/. The only amendment
added explicit import-path initialization before the unchanged scan.

The amended scan completed 32/32 slots from 16 deterministic 8-ply opening
roots, both candidate colors per root, uniform material model on both sides,
shared task2492 AlphaBeta/Receipt search, D2/q0, maximum 20,000 combined
candidate+foe nodes per slot, 8,192 nodes/2 s per query, and 600 s global cap.
It used 413,628 total nodes (201,293 candidate; 212,335 fixed foe), 3,352
queries, and 48.006 s. Fourteen slots stopped at an actual rule terminal, but
only a boolean stop reason was retained; no winner/draw value, W/L label,
weights, fitness, or endpoint ranking was read or emitted. No search was
incomplete. The audit verifies all 32 unique slots, node decomposition/caps,
and absence of outcome/weight keys.

The 1.50 s/slot mean projects 1,024 future evaluation slots to 25.6 min.
A cap-based projection at 20,000 nodes per slot and observed aggregate
throughput projects about 39.6 min. This cost-only sample uses uniform policies
and is not a guarantee for trained endpoints or games with different lengths.
The roots are explicitly excluded from any future strength panel.

For planning only, the task2612 combined 800k-node shared-receipt run took
111.982 s (method order confounded); linear scaling to 4M per each of TreeStrap
and TDLeaf is roughly 18.7 min. Existing task2568 WDL used 4M nodes in 494.221 s
and its recorded evaluation paths cost additional work. Combining two learner
training arms, one WDL arm and 1,024 evaluation slots gives a rough 53–67 min
search estimate before setup/audit overhead. A frozen all-in 110-minute cap
would leave a material reserve and remain below the 120-minute prior-assessment
threshold; re-estimate before registration if the source or panel changes.
No actual W/L comparison is registered or launched by this scan.
