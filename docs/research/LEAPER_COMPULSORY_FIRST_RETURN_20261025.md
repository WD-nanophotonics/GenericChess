# Pure-Leaper compulsory continuation and first ordinary return — 2026-10-25

Final qualification: all registered producers are CLOSED. The intermediate c9b521fd checkpoint correctly reported its then-running guard; completed results below supersede that pending status. Production/default behavior is unchanged. All observations concern exposed TRAIN histories from one pure-Leaper RuleSet, not strength or class-wide success.

## Completed findings

The p53 error is not explained solely by unequal root allocation. With fresh TT and full-window equal child depth, all nine children completed D6 and still ranked a DRAW ahead of the unique WIN. At full remaining-clock D10, all nine completed and replayed legally: eight DRAW and one WIN. These 18 queries cost 744.176 query seconds and replayed 144 legal PV steps. This is a cold-search witness, not the missing original warm-root trace or an independent solver.

Three research-only continuation policies were tested on four fixed exposed cases at the existing 45-second/10-million-node limits. Noncheck-singleton Q continuation repaired p53 but regressed p49 (3/4, unchanged aggregate); branching-depth main continuation achieved 2/4 with no repair and one regression; restricting singleton Q continuation to the ordinary boundary again repaired p53 and regressed p49 (3/4). All three fail their no-regression gate and are rejected for activation or larger panels. Noncheck singleton does not prove the move is quiet. Branching depth is not ordinary ply depth. A pilot key typo caused a preserved pre-query failure after one return; only its three unexecuted slots were subsequently run, without repeating that paid query.

A separate first-Q refinement keeps the initial D1 Q0 fallback, clears TT once at the Q semantic boundary, adds D1 Q4, then proceeds to D2+. In the four-case pilot, final quality stayed 3/4 without repairs/regressions; p53 remains wrong. On p7 the first correct internal result appeared at D1 Q4 in 0.05985 seconds /234 search events, versus historical D2 in 0.10250 seconds /428 events. The repeated D1 callback is not D2. Internal first-correct time is not yet evidence that a consumer receives a better action. Other first-correct latencies were slower. Historical timings have concurrent-load and source-overhead limitations.

This narrow pilot passed the preregistered gate for one remaining-60-history guard; the guard subsequently closed with immutable source and no cap refill. The separate two-callback consumer-return test then completed; final measurements follow below. No production flag or shared backend was changed.

## Evidence and verification

Lossless gzip publication copies, plans, returned queries, iteration traces, qualifications, receipts and assessments are under [the evidence directory](data/leaper_compulsory_first_return_20261025/manifest.json). The manifest distinguishes private-original hashes from sanitized publication bytes. Source snapshots are data, not executable entry points. Read-only verifiers live in scripts/verify_leaper_branch_allocation.py and scripts/verify_leaper_forced_continuation.py. Fixed reference labels are from the previously pinned AUX public evidence; AUX work was not rerun or modified.

The original twenty targeted tests cover replay contracts, aborted-budget/cancellation behavior, unchanged first-Q fallback, actual semantic TT clearing, and singleton depth boundaries. One prototype test initially reused a baseline EXACT TT entry across different policy semantics; the cause was diagnosed and the test corrected to use a fresh context while preserving its terminal-score assertion. No expected static value was changed to match current output.

## Current decision and consultation

Reject the three singleton policies. The frozen first-Q guard and actual consumer test are complete; prioritize the bounded p53 causal-frontier specification. Ask Dot whether the evidence supports prioritizing early ordinary evaluation independently of p53, and whether the equal-D6 versus full-clock-D10 witness warrants a narrowly instrumented quiet-threat mechanism study rather than another continuation threshold. Neither advice nor a missing reply is a publication/work gate.

User correction: each new work round must start a fresh mailbox TYPE=AGENT_REQUEST; old-thread FOLLOWUP does not trigger that consultation. This round is correcting that missed trigger after publishing this checkpoint; the active research session continues.

## Completed guard and actual consumer results

The 4 pilot plus remaining 60 histories all returned, with 468 replayed legal PV steps. At the original 45-second cap, default and refined each preserve WDL on 63/64 cases: zero repairs and zero new regressions. p53 remains wrong. All first-Q0 prefixes match the paid controls exactly and frozen backend/policy hashes still match. Candidate query time totals 2,596.103 seconds across 64 cases. This is a quality guard on exposed histories, not an independent holdout or proof of no regression elsewhere.

The subsequent frozen two-callback consumer produced all 128 actual returns, with 191 legal PV steps and zero incomplete ordinary goals. Both arms preserve WDL on 61/64 cases, including 27/30 choice-sensitive histories; zero paired repairs/regressions. Refined/default paired return-latency median is 0.6682. Total query times are 2.3823 versus 4.2341 seconds, and search events 8,083 versus 15,280. Median cancellation-to-return tails are 0.0441 versus 0.0359 milliseconds; maximum tails 0.0498 versus 1.1478 milliseconds. Raw return sources and all timing fields are retained. The lower work and early-return latency are a scoped local positive, while final quality is unchanged.

These compare a specific two-completed-callback consumer: refined D1Q0→D1Q4 versus default D1Q0→D2Q4. They are not equal-depth or equal-time arms. The 2-second cap is a guard, not an equal wall budget actually spent. No general anytime advantage, strength gain, default activation or wider rule-class success follows. First-Q refinement stays research-only secondary work.

A fresh offline ladder from the already-paid nine cold child searches reproduces the horizon reversal: child D5 ranks unique-WIN branch8 first (root score1103), then child D6 ranks DRAW branch1 first (1106), corresponding nominally to root D6→D7. The decisive-child audit verifies full histories/actors, completed full-window calls inferred from pinned default source, and D6 PVs ending ongoing with four clock plies; D10 reaches max-ply DRAW versus checkmate WIN. Actual recursive bound/frontier events were not recorded. This weakens an allocation-only explanation without establishing the original warm-root chain or a specific missing quiet threat.

The guard plan's question/revision prose inherited the singleton template, while its actual policy, selected keys, limits and hashes were fixed correctly as first_q_refinement. A separate metadata clarification preserves that original plan instead of rewriting its preregistration. The consumer's original unexecuted source/plan is retained alongside the pre-execution observation-only amendment adding actual return source/cancellation tail after Dot advice; no slots or limits changed.

## Communication, accounting and next useful step

New-round AGENT_REQUEST GC-SLACK-20261025-101229-19c1f677 was delivered and exact-readback verified at root1792890794.866589. Its one five-minute follow-up read captured solicited Dot reply1792890925.877869; autonomous Chat comment1792890455.776499 was separately saved with its full thread and assessed. Adopted advice: distinguish callback strategies from common-deadline anytime claims, capture actual return source/tail, and prioritize a causal frontier over singleton sweeps. Neither advisor independently ran these queries/tests. Every logical Slack opening now checks new comments and relevant threads; each Dot send has one delayed reply check, not repeated polling.

This segment made 222 successful Player calls. A pre-query key-binding failure after one successful prefix was preserved, with only its three unexecuted slots continued. The work ledger credits actual timezone-aware intervals; one subresolution consumer interval has identical UTC start/end and is explicitly uncredited despite a positive performance-clock measurement. Administration, transport, old findings and idle gaps receive no time credit. Session completion requires a matching quality review, finish and final-check.

Main returns to p53 causal-frontier diagnosis; the next specification begins by binding only the two decisive cold branches and inventories missing scalar return/window/path fields, with bounded capture/truncation and no WDL input to execution. No new query is started from the missing old observer slot. Existing first-Q measurements remain a secondary scoped candidate. Keep production/defaults and AUX unchanged.
