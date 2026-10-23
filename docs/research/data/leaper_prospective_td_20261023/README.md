# Prospective TD and clock-aware truth evidence

Report: [Prospective TD and truth costs](../../LEAPER_PROSPECTIVE_TD_AND_TRUTH_COST_20261023.md).

These five compressed packets preserve complete rules and histories, positive
and negative results, failed graph caps and the actual executed model endpoints.
They contain no serialized pickle graphs. Producer sources inside packets are
evidence strings, not instructions to execute.

| Packet | Contents |
| --- | --- |
| `games.json.gz` | All 384 slots, 32 prefixes, 62 distinct complete records and 3,482 metadata-selected query/PV examples |
| `targets.json.gz` | All 9,803 actual training-target rows, 256 final outcomes and 16 batch endpoints |
| `mechanisms.json.gz` | Nineteen literal finite-depth trees, tie controls, integer-gap bounds and both NEW first-action/tail interventions |
| `larger_truth.json.gz` | Three bounded parent attempts, short-clock actual-history proof, complete capture-child input and one-sided parent bound |
| `structural_truth.json.gz` | Fixed-source new-rule census, both frozen component plans,169 labelled histories, actual query references and two local horizon/price controls |

From the repository root, run the readers with the project Python environment:

```powershell
$d = 'docs/research/data/leaper_prospective_td_20261023'
.venv/Scripts/python.exe "$d/verify_games.py" "$d/games.json.gz" --output artifacts/prospective-games-check.json
.venv/Scripts/python.exe "$d/verify_targets.py" "$d/targets.json.gz" --output artifacts/prospective-targets-check.json
.venv/Scripts/python.exe "$d/verify_mechanisms.py" "$d" --output artifacts/prospective-mechanisms-check.json
.venv/Scripts/python.exe "$d/verify_larger_truth.py" "$d/larger_truth.json.gz" --output artifacts/prospective-truth-check.json
.venv/Scripts/python.exe "$d/verify_structural_truth.py" "$d/structural_truth.json.gz" --output artifacts/structural-truth-check.json
.venv/Scripts/python.exe "$d/verify_history_certificates.py" "$d/structural_truth.json.gz" --output artifacts/history-certificates-check.json
```

The game reader replays every outcome and all supplied examples, rather than
claiming the compact packet retains every private query PV. The private full
reader checked all 25,926 queries and 101,415 PV edges. Counts and CPU times are
reported execution receipts, not independently certified CPU measurements.

The truth reader rebuilds the 65,760-position / 500,048-edge child component via
shared Core, checks Bellman/rank equations, its structural deadzone and all
root-action bounds, then binds the actual capturing edge to the parent. It also
enumerates the 1,220 descendant calls in the three-ply actual-history tree,
including repetition and max-ply terminals. Root dispatch is not included in
that descendant counter. It never upgrades either partial parent graph.

The first reader draft incorrectly used a nonexistent compiled `ruleset`
attribute, then counted root dispatch as an additional descendant. The corrected
reader uses the saved complete RuleSet clock and the declared descendant-counter
convention; unchanged terminal counts and action WDL agree. Those development
errors did not change experiments, graphs, models or caps.

The shared Core is the same authority as the producers. These checks are
independent replays/rebuilds, not independent engine or unconditional history
quotient proofs. The public reader's single 240-second cooperative guard may
interrupt on a slower machine; an interrupted verification supplies no labels.
Cached old 4x4 graph annotations in the mechanism packet are explicitly reused,
not rebuilt by the mechanism reader.

The structural reader separately rebuilds33,584 and49,928 entries and all their
edges, then checks all360 covered query references. Its240-second cooperative
guard is per component. The packet identifies the exact committed source price
packet and its hash; all960 source forward games remain OLD. The first component
has no unresolved immediate-win decision; the second attempt explicitly adds a
positive-depth-return condition after that observation. It is adaptive post-hoc
diagnosis, not an independent holdout. The169 histories and360 query references
are deliberately distinguished, as are the two FLOOR-error references at one
history. No source code embedded as text is automatically executed.

The same packet preserves four higher-material proof preflights, the failed
fourth-result wrapper, one separately costed technical recovery, four child
proof calls and two exported WIN certificates. The certificate reader does
not rerun their searches. Three original roots and the S4 child stay UNKNOWN;
no depth-budget failure is a draw label. Both root/child certificates are bound
to the actual complete rules and full histories. The original fourth lost
payload is not described as verified evidence or a successful initial attempt.
