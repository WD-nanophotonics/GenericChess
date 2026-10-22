# Resource generation and material evidence — 2026-10-22

This is a technical publication copy of PRIMARY's closed experiments. It contains
complete canonical rules, full typed GameRecords, every retained PlayerDecision
field, source snapshots, input/record hashes, failures and UNKNOWN outcomes.
GameStates are reconstructed with complete histories and checked against hashes.
Private originals, account/Chat headers, tracebacks and session logs are excluded.

From the repository root:

```powershell
.\.venv\Scripts\python.exe -X utf8 -m docs.research.data.resource_generation_material_20261022.verify
```

The reader performs no search, fitness or training. It uses the existing full
Core, not a second engine or WDL oracle. Its offline measurement requires only
the fixed parent capsule `../small_rule_family_20261022/observations.json.gz`,
whose SHA is in the manifest. It replays the necessary 256 parent games, not
all closed parent campaigns. There are no network reads during verification.

`observations.json.gz` keeps unique new trajectories once. Fourteen preference
frames reference the exact already-qualified source game. Twelve invalid initial
slots remain failures; they are not secretly repaired or replaced. Exact layout
fractions describe only their finite parent set. Source snapshots are historical
experimental evidence; the maintained runnable entrypoint here is `verify`.

`next_*` is a distinct frozen future plan: 24 NEW games at common Unit ordering,
all 12 exposed preferred rules. Static fields and actual AST slots are checked;
there have been zero Player queries and no fitness execution for that plan.
`next_runner.py` is the exact local producer snapshot; its fixed ignored input
location and existing local helper imports must be restored before execution.
The completed material experiment is not rerun by these files.
