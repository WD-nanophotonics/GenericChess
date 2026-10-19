# DEV_AUX task2610 — Second root-panel result

## Result and audit

The frozen task2606 models were evaluated on a second outcome-blind, pre-classified root panel. Attempt 2 completed all 1,536 registered slots in 702.419 seconds (2,201,293 search nodes; 39,958 queries), below the frozen 1,200-second cap. Independent slot/query/history replay passed: 64 distinct full start histories, 1,437 actual terminals and 99 censored UNKNOWN horizons; all 39,958 searches completed. Attempt 1 remains a preserved pre-output schema failure; attempt 2 changes only the required registration hash alias, not models, roots, plan, conditions, or cap.

Endpoint totals for task2610: initial 234W/8D/244L/26 UNKNOWN; TD95 297W/2D/174L/39 UNKNOWN; LocalLambda 299W/5D/174L/34 UNKNOWN.
Provenance reconciliation PASS: attempt 2 binds the preserved attempt-1 failure and unchanged model/plan/root hashes; all 23 source pins match. See provenance-audit.json.

## Paired finite-panel bounds

| Panel | TD95 − initial | LocalLambda − initial | LocalLambda − TD95 |
|---|---:|---:|---:|
| task2609 | [-0.0488, +0.3809] (UNKNOWN pairs 55/512) | [+0.0430, +0.4414] (UNKNOWN pairs 51/512) | [-0.1406, +0.2891] (UNKNOWN pairs 55/512) |
| task2610 | [+0.0469, +0.4688] (UNKNOWN pairs 54/512) | [+0.0195, +0.4414] (UNKNOWN pairs 54/512) | [-0.2441, +0.2402] (UNKNOWN pairs 62/512) |

LocalLambda-minus-initial has positive conservative lower bounds in both panels. TD95-minus-initial is positive on the second panel, but its first-panel bound includes zero. LocalLambda-minus-TD95 includes zero in both panels, so the learner-method contrast remains unresolved and there is no reproduced ranking. These are paired finite-panel bounds, not confidence intervals or independent replicates.

## Reproducibility artifacts

The exact query/game streams are retained locally and published as deterministic gzip files. compressed-streams.json records original/archive sizes and SHA-256; both archives decompress byte-for-byte, and credential-pattern scans pass. Cross-task archive verification reproduced task2606/task2609 archive hashes and decompressed originals; see archive-verification.json.

| Stream | Rows | Raw bytes | Gzip bytes | Gzip SHA-256 |
|---|---:|---:|---:|---|
| eval-queries | 39,958 | 237,337,652 | 3,276,835 | e9132bae4390b44c6e2d48de4bbead169545640c7ba716cbe45309b2036ae45a |
| eval-games | 1,536 | 4,181,646 | 118,677 | a8750001aa0b36b8bec15c4fb1a3a9bbfe7adc9c4c971352cad9b6d487c9e264 |

## Per-rule outcome and UNKNOWN profile

These exact rule strata are descriptive: each panel contributes 128 paired root/seed/color slots per rule, and are not independent rule samples. The high UNKNOWN concentration is visible in rule271003 and explains much of the width there.

| Panel | Rule | Initial W/D/L/U | TD95 W/D/L/U | LocalLambda W/D/L/U | LL − TD95 bound |
|---|---:|---:|---:|---:|---:|
| task2609 | 271001 | 58/1/66/3 | 66/0/61/1 | 69/0/58/1 | [+0.031, +0.094] (U 2) |
| task2609 | 271002 | 54/1/73/0 | 86/0/42/0 | 98/2/28/0 | [+0.203, +0.203] (U 0) |
| task2609 | 271003 | 59/3/40/26 | 59/0/38/31 | 66/0/32/30 | [-0.766, +0.891] (U 53) |
| task2609 | 271004 | 73/0/54/1 | 75/0/53/0 | 73/0/55/0 | [-0.031, -0.031] (U 0) |
| task2610 | 271001 | 64/1/60/3 | 77/0/50/1 | 78/0/49/1 | [-0.016, +0.047] (U 2) |
| task2610 | 271002 | 60/1/67/0 | 94/0/34/0 | 92/1/35/0 | [-0.023, -0.023] (U 0) |
| task2610 | 271003 | 48/6/51/23 | 56/2/32/38 | 59/4/32/33 | [-0.938, +0.938] (U 60) |
| task2610 | 271004 | 62/0/66/0 | 70/0/58/0 | 70/0/58/0 | [+0.000, +0.000] (U 0) |


## Seed-stratified descriptive bounds

Each seed contributes 128 paired root/color strata. The bounds below remain deterministic finite-panel UNKNOWN bounds; these four model seeds were crossed over all roots and are not independent replicates.

| Panel | Seed | TD95 − init | LocalLambda − init | LocalLambda − TD95 |
|---|---:|---:|---:|---:|
| task2609 | 1977 | [-0.102, +0.148] (U 8) | [+0.023, +0.430] (U 13) | [+0.008, +0.352] (U 11) |
| task2609 | 8173 | [+0.016, +0.609] (U 19) | [+0.070, +0.633] (U 18) | [-0.180, +0.320] (U 16) |
| task2609 | 27182 | [+0.148, +0.492] (U 11) | [+0.164, +0.352] (U 6) | [-0.234, +0.109] (U 11) |
| task2609 | 31415 | [-0.258, +0.273] (U 17) | [-0.086, +0.352] (U 14) | [-0.156, +0.375] (U 17) |
| task2610 | 1977 | [+0.047, +0.391] (U 11) | [-0.008, +0.367] (U 12) | [-0.266, +0.234] (U 16) |
| task2610 | 8173 | [+0.148, +0.648] (U 16) | [+0.031, +0.656] (U 20) | [-0.242, +0.289] (U 17) |
| task2610 | 27182 | [+0.055, +0.492] (U 14) | [+0.156, +0.469] (U 10) | [-0.141, +0.203] (U 11) |
| task2610 | 31415 | [-0.062, +0.344] (U 13) | [-0.102, +0.273] (U 12) | [-0.328, +0.234] (U 18) |

## Scope and preserved limitations

task2609 and task2610 use disjoint exact rule-plus-full-history roots (64 each; zero intersections), while each panel crosses the same frozen model seeds across roots. The panel comparison is a root-sensitivity check on one frozen trained model set, not seed replication, a descendant-history holdout, or population/generalization evidence. Do not select the more favorable panel. The 99 new UNKNOWNs remain censored, never draws.

Attempt 1 failure, registration repair, both frozen root panels, complete JSONL streams, and independent audits remain separate evidence. No engine defaults, UI, primary checkout, or other role state changed.

Machine-readable panel table and audit hashes: `results/dev_aux/task2610/panel-comparison.json`. Attempt-2 replay audit: `results/dev_aux/task2610/attempt-2/audit.json`.
