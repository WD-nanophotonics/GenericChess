# Curated natural-history and ABC price evidence

Report: [Natural decision capacity, depth and fixed ABC prices](../../LEAPER_NATURAL_PRICE_CAPACITY_20261023.md).
Source rules/histories: PRIMARY `55abf3de22f20ac03eb07b5260284466173a3264`.
Shared infrastructure and next-context inputs: sandbox
`ff72649685c21a37bdbe147c930e4b2070934f77`.

The five gzip files total951,632bytes. `manifest.json` records their exact hashes.
Full graphs, pickle caches, temporary drivers and raw query trajectories remain
ignored. These are curated replay projections, with separate public/private
verification scopes.

| File | Contents |
|---|---|
| `natural.json.gz` | All2047 census histories, inclusion conditions,24 graph roots/full rules,898 qualified root labels and4490 D1 calls |
| `mechanisms.json.gz` |5388 D2/D4 receipts,1796 Unit optimal-action sets and residual D6/D8 controls |
| `abc_grid.json.gz` | All576 continuation-slot outcomes,101 deduplicated full GameRecords,929 metadata-selected query examples |
| `abc_validation.json.gz` | All256 prospective-slot outcomes,116 deduplicated full GameRecords,1151 metadata-selected query examples |
| `selection_and_mechanism.json.gz` | Predeclared selection/validation rule,selected price and45 literal first-divergence trees/128 paired controls |

The compact game packets contain full frozen RuleSets, opening records, seeds,
roles, actual model parameters, limits, final records and per-slot measured costs.
They also embed the executed producer source and exact raw-JSONL hash. Deduplicated
records are references, not extra games. Initial terminal-prefix views stay in
the planned denominator and have no new controller continuation.

The full private readers checked every39987/19408 query and156329/75934 PV edges.
The public game reader checks every compact outcome and complete record, plus
only the929/1151 published query examples. It reconciles cost metadata; it does
not independently certify physical CPU work or reconstruct unpublished PVs.
`verification.json` preserves both scopes and the original measured counts.

Run from the repository root at the published revision, using the project Python
environment. Outputs below belong in ignored `artifacts/`:

```powershell
$d = 'docs/research/data/leaper_natural_price_capacity_20261023'
.venv/Scripts/python.exe "$d/verify_natural.py" "$d/natural.json.gz" --source-from-git --output artifacts/natural-price-verify.json
.venv/Scripts/python.exe "$d/verify_mechanisms.py" "$d/natural.json.gz" "$d/mechanisms.json.gz" --output artifacts/natural-mechanism-verify.json
.venv/Scripts/python.exe "$d/verify_games.py" "$d/abc_grid.json.gz" --output artifacts/abc-grid-verify.json
.venv/Scripts/python.exe "$d/verify_games.py" "$d/abc_validation.json.gz" --output artifacts/abc-validation-verify.json
```

The natural reader rebuilds every component through shared Core. Its2400second
whole/240second-per-component verification limits preserve resource failure as
failure, never new WDL labels. Observed full rebuild1853.951seconds; it includes
959604 summed graph entries with component overlap, not independent cases.
The original-census option reads the exact55ab Git blob at
`docs/research/data/small_rule_family_20261022/observations.json.gz` and verifies
its hash,2060references/2047histories and origins. The object must exist locally.
`--census-only --source-from-git` checks that census without rebuilding graphs.
Without `--source-from-git`, semantic checks apply to the supplied manifest.

The mechanism reader uses literal full-history Core trees and the stored PVs;
it does not use the old fresh-repeat-two D4 shortcut. `--residual-only` checks
only the extra D6/D8 trees. Local full mechanism and residual passes were run
separately,69.326 and27.940seconds. Rule-scope assertions were additionally
exercised on all24 RuleSets. Shared Core verification is not an independent
rules implementation or a general history quotient.

The first-divergence observer's executed source is embedded in its packet.
Its branch score vectors cover the nine finite prices at each actual shared
history; they do not assign minimax WDL to the subsequent complete-game effect.
Full-support equality(12pairs) and both served actions remaining co-optimal
under both prices(21pairs) are different counts.

`next_context_cost.json` is the first16 cold-root cost calls on PRIMARY's two
already exposed newer ABC codes/four layouts. It is not a game/TD performance
claim, a full-game forecast or an adoption of PRIMARY's generator/screen/label
cycle. The current fixed-price grid and prospective validation stay separate;
no TD training or production default change is included.
