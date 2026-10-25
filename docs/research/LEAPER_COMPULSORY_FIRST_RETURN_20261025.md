# Pure-Leaper compulsory continuation and first ordinary return — 2026-10-25

This is an intermediate published checkpoint. The 60-history first-Q guard is RUNNING; this report does not qualify it as complete. Production/default behavior is unchanged. All observations concern exposed TRAIN histories from one pure-Leaper RuleSet, not strength or class-wide success.

## Completed findings

The p53 error is not explained solely by unequal root allocation. With fresh TT and full-window equal child depth, all nine children completed D6 and still ranked a DRAW ahead of the unique WIN. At full remaining-clock D10, all nine completed and replayed legally: eight DRAW and one WIN. These 18 queries cost 744.176 query seconds and replayed 144 legal PV steps. This is a cold-search witness, not the missing original warm-root trace or an independent solver.

Three research-only continuation policies were tested on four fixed exposed cases at the existing 45-second/10-million-node limits. Noncheck-singleton Q continuation repaired p53 but regressed p49 (3/4, unchanged aggregate); branching-depth main continuation achieved 2/4 with no repair and one regression; restricting singleton Q continuation to the ordinary boundary again repaired p53 and regressed p49 (3/4). All three fail their no-regression gate and are rejected for activation or larger panels. Noncheck singleton does not prove the move is quiet. Branching depth is not ordinary ply depth. A pilot key typo caused a preserved pre-query failure after one return; only its three unexecuted slots were subsequently run, without repeating that paid query.

A separate first-Q refinement keeps the initial D1 Q0 fallback, clears TT once at the Q semantic boundary, adds D1 Q4, then proceeds to D2+. In the four-case pilot, final quality stayed 3/4 without repairs/regressions; p53 remains wrong. On p7 the first correct internal result appeared at D1 Q4 in 0.05985 seconds /234 search events, versus historical D2 in 0.10250 seconds /428 events. The repeated D1 callback is not D2. Internal first-correct time is not yet evidence that a consumer receives a better action. Other first-correct latencies were slower. Historical timings have concurrent-load and source-overhead limitations.

This narrow pilot passed the preregistered gate for one remaining-60-history guard; that guard is currently running with immutable source and no cap refill. A separate two-callback consumer-return test is prepared but will run only after the guard closes. No production flag or shared backend was changed.

## Evidence and verification

Lossless gzip publication copies, plans, returned queries, iteration traces, qualifications, receipts and assessments are under [the evidence directory](data/leaper_compulsory_first_return_20261025/manifest.json). The manifest distinguishes private-original hashes from sanitized publication bytes. Source snapshots are data, not executable entry points. Read-only verifiers live in scripts/verify_leaper_branch_allocation.py and scripts/verify_leaper_forced_continuation.py. Fixed reference labels are from the previously pinned AUX public evidence; AUX work was not rerun or modified.

Twenty targeted tests cover replay contracts, aborted-budget/cancellation behavior, unchanged first-Q fallback, actual semantic TT clearing, and singleton depth boundaries. One prototype test initially reused a baseline EXACT TT entry across different policy semantics; the cause was diagnosed and the test corrected to use a fresh context while preserving its terminal-score assertion. No expected static value was changed to match current output.

## Current decision and consultation

Reject the three singleton policies. Finish the frozen first-Q guard, then measure actual early consumer return if permitted by its result. Ask Dot whether the evidence supports prioritizing early ordinary evaluation independently of p53, and whether the equal-D6 versus full-clock-D10 witness warrants a narrowly instrumented quiet-threat mechanism study rather than another continuation threshold. Neither advice nor a missing reply is a publication/work gate.

User correction: each new work round must start a fresh mailbox TYPE=AGENT_REQUEST; old-thread FOLLOWUP does not trigger that consultation. This round is correcting that missed trigger after publishing this checkpoint; the active research session continues.
