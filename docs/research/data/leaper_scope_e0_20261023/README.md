# Scoped E0 evidence and strict initial-mu handoff

`evidence.json.gz` contains21selected technical documents plus source snapshots,
full rules/histories, local closure evidence, exact witnesses, missing inputs,
frozen forecasts and cost/score limits. `manifest.json` binds compressed and
decoded bytes. Private originals and all old experiments remain unchanged.
No raw Slack/account/session logs or credentials are published.

Run once from the repository root, with a NEW ignored output directory:

```powershell
.\.venv\Scripts\python.exe -X utf8 -m scripts.verify_leaper_scope_e0 --bundle docs/research/data/leaper_scope_e0_20261023/evidence.json.gz --output .local_agent/scope-e0-public-check
```

The reader first verifies the bundle and document hashes, then recovers the
original scientific JSON serializations only when their byte hashes match.
This is deterministic source recovery, not reconstruction of a lost tool return.
It checks all scoped single-entity transitions through public APIs, full initial
records/setup keys, one-ply features/witnesses, finite rate-error bounds and the
new literal fork index. It does not run a Player, learner or H6history solver.
The old public `leaper_e0_20261023` packet is a required fixed prerequisite.

The sources include execution snapshots and explicitly marked publication
versions; do not attribute every old timer to the final source. Existing shared
Core is an authority for semantics, not an independent engine/WDL oracle.

Strict forecast exports are generated AFTER the technical source commit and
included in the final delivery. They contain both existing AUX formats:
conditional-history predictions and family-mean prevalence predictions. Exact
support-ID mu aliases are bijective; the unavailable twelfth family has no
fabricated row. V1predictions stay frozen; colour v2is exposed development.
Cost dictionaries count actual feature returns/edges, with shared whole-producer
wall time reported once. They are not per-query timing or a runtime speed claim.


`forecasts.json.gz` is the actual strict export from committed source
`cffcd6d2975375d3a91dfce325c4bb48559c2516`; its own manifest binds the bytes.
Eight methods each have3616conditional-history rows and11family-rate rows.
This commit contains the exporter; the earlier feature-run code hashes and Core
baseline remain separate in the evidence. No feature query was rerun for export.

For a NEW matching truth object supplied/verified by AUX, select a method object:

```python
import gzip, json
from pathlib import Path
packet = json.loads(gzip.decompress(Path(
    'docs/research/data/leaper_scope_e0_20261023/forecasts.json.gz').read_bytes()))
conditional = packet['history_forecasts']['oneply_augmented_cooperative']
prevalence = packet['rule_prevalence_forecasts']['oneply_augmented_cooperative']
```

Use the corresponding existing history or prevalence scorer. Do not pass the
entire outer packet as a single forecast and do not reuse old ten-rule truth by
mask string. `mu_aliases` binds the old names to exact sorted complete State IDs.
The two score targets differ; AUX's positive-improvement sign is opposite to this
report's model-minus-baseline loss difference. No independent scoring is claimed.
