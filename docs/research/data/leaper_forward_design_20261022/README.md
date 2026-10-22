# Pure-Leaper forward-design evidence

Read the [report](../../LEAPER_FORWARD_DESIGN_20261022.md) for scope and conclusions.
`manifest.json` gives actual compressed/decoded sizes, hashes and source hashes.
`observations.json.gz` is a technical publication copy, not private account logs.
It retains complete canonical rules, strict GameRecords, full final GameStates,
all returned controller decisions, cost/profile data, finite-codebook diagnostics,
actual producer sources and the separately prepared NOT-RUN next cohort.

Current games are540physical executions. RNG/FLOOR turns are not AlphaBeta calls.
The first480executions include331unique full histories; no independent-sample CI
is claimed. Original setup/terminal aggregation failures remain private; the
technical copy describes60recovered games without actual private-path tracebacks.
No fitness was rerun. The32contract checks cover the observed caller contracts.

Validate THIS copy from the repository root:

```powershell
.\.venv\Scripts\python.exe -X utf8 -m scripts.leaper_portrait --packet docs/research/data/leaper_forward_design_20261022/observations.json.gz --receipt .local_agent/leaper-reader.json
```

The reader checks every retained action/full history, literal PV, terminal and
utility; it also replays actual uniform RNG/FLOOR stream consumption. It uses the
same production Core, not an independent engine or an all-game WDL oracle. Source
privacy review, scientific interpretation and actual remote delivery are separate.
No search/fitness/training is needed to read/verify the packet.

`scripts.leaper_design` is the maintained small forward-probe command. Use a NEW
ignored output for prepare/preflight/run; never rerun a frozen results directory.
Its optional material mode requires `preflight-inputs.json` with complete saved
root records, including a nonempty natural history per ready world, before any
cost query. Both Adapter policies and exact material components are then checked.
The packet includes those actual full-history inputs, not an artificial stub.

All source snapshots retain actual UTF-8 bytes/line endings; run registrations
bind their producer hashes. `next` contains complete future inputs/registration,
predeclared forecasts and10cold returns, but0fitness games. It is gameplay-new
within an initial-codebook-exposed space, not an independent unseen-rule holdout.
