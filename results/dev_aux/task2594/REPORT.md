# DEV_AUX task2594 — terminal-target local-lambda TD on standard Chess

**Result: finite-panel gate passes; Generic transfer is justified as the next pilot, not as a general-learning claim.**

## Frozen question and protocol

The registered question was whether the `OutcomeGatedTDLeafEpisode` update improves standard-Chess W-L against both frozen TD(lambda=.95) and the same initialization at equal candidate training-node cost. Four frozen seeds (1977, 8173, 27182, 31415) each received 1M candidate nodes. The evaluation paid 768 slots over 128 fresh exact-history roots total, allocated as a different 32-root block to each seed; each root is evaluated on both colors for initial, baseline, and candidate endpoints. See task2603/REPORT.md for the outcome-blind allocation audit and the cross-seed interpretation limit. Opponent weights were uniform; search was depth 2, at most 8192 nodes/2 seconds per query, and 1024 plies. Only actual ChessEnv terminal outcomes count; this run completed all slots within its 2100-second cap.

The candidate update sets the residual trace lambda to 1 only when the next observed search target has `pv_terminal=true`; otherwise it uses .95. Final known-outcome residuals use .95. UNKNOWN outcomes are censored from training, and incomplete searches are not observations.

## Results

| Endpoint | W | D | L | U | Score (W + D/2) / 256 |
|---|---:|---:|---:|---:|---:|
| Same initialization | 142 | 43 | 71 | 0 | 0.639 |
| Frozen TD(.95) | 198 | 31 | 27 | 0 | 0.834 |
| Candidate local-lambda | 220 | 21 | 15 | 0 | 0.900 |

The preregistered slotwise reward-difference interval averaged over all 256 matched `(seed, root, color)` slots is exactly **+0.1328** candidate vs. TD(.95) and **+0.5234** candidate vs. initialization. All 768 slots ended in actual termination, so no UNKNOWN/missing bound widened these finite-panel intervals.

Independent training replay passed: 4M candidate nodes, 253 games (210 actual terminals, 43 UNKNOWN), 36,526 queries, 18,272 observed searches and 18,229 TD residual terms. Candidate terminal-PV target residual exposure is 216 pooled (54/64/55/43 per seed), exceeding the 128 gate; baseline exposure is 186 (37/66/38/45). Independent deployment replay passed all 768 slots and their full histories, selected endpoints, actors, foes, terminal results, and paid-node totals: 12,977,683 nodes, 119,552 queries, 768 actual terminals, zero UNKNOWN, in 1711.1 seconds. The fresh root manifest and frozen source/runner pins were checked before training.

## Interpretation and limits

All preregistered finite-panel conditions passed, so this supports carrying the *same* learner into a Generic-rule pilot. It does not show stable learned price ordering: per-seed candidate rankings differ substantially. It is not a full historical TD/TreeStrap reproduction, a population estimate, a human-price fit, or evidence for arbitrary Generic rules. Each seed has a different 32-root EVAL block. Candidate-versus-baseline comparisons remain paired within each seed/root/color slot, but between-seed differences combine initialization and root-block differences. The 256 candidate-versus-TD slot pairs are a finite panel, not 256 independent roots; see task2603/REPORT.md. No Generic training was done in this task and no product default/UI was changed.

The full raw query streams remain in this checkout because they are large; this commit includes the game traces, root manifest, exact replay scripts and audit summaries. Raw trace SHA-256:

- `train/queries.jsonl` (81,958,861 bytes): `FD272822515BF499D12CAD9CCC53D43E41C585EBFF82DAB5527AEF6C581BFD66`
- `eval-queries.jsonl` (291,099,990 bytes): `AC7FF2BF5F455D421A1F68AD47B4D645E8990C1B34D6554E64BCFA73A03E8B61`

Next: register one bounded Generic-rule transfer using this learner and complete Generic rule semantics, with frozen opponent/budget and actual W/L/D validation; retain the old WDL grid as a cost-matched control. Do not infer stable price order from this Chess result.
