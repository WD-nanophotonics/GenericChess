# Search windows, complete-state caller and policy evidence

Read [summary.json](summary.json) first. [measurements.zip](measurements.zip)
contains138 explicitly selected, exact technical JSON files (24.8MB unpacked).
[manifest.json](manifest.json) gives every member hash/size and the archive hash.
Raw project Chat/account/pytest logs and credentials are excluded. Complete
RuleSets, strict GameRecords, original query fields, failures/UNKNOWN and the
slot31 eligibility correction are preserved. The small current control inputs
are also directly readable JSON here; their balanced queries are NOT executed.

The public product/default API is unchanged. The maintained
`scripts/semantic_probe_cost.py` exposes existing PVS, aspiration, staged ordering
and an explicit complete-type Unit control; it also preserves prepared inputs
and failures. Use its `--input` full canonical format and a NEW output path.

`study.py` is the thin existing-runner study adapter, corrected AFTER the frozen
run to honor whole-runner qualification. `study-original.patch` reconstructs the
actual measured producer; original/corrected hashes are in the packet. Never
rerun a closed protocol to refill a missing outcome. `repeat_probe.py` still pays
every evaluation: its dictionary verifies repeats, it does not reuse values.

Historical CLI patches `pvs-measured.patch` and `asp-unit-measured.patch` each
apply independently to `scripts/semantic_probe_cost.py` at
`f92d739dec3b7454c58fc2d7709e7233156633e6`, not successively. LF and CRLF source
hashes are recorded and byte-verified. The intermediate
`search-asp-measured.patch` documents the first post-proof budget check used by
the aspiration/Unit study. It is historical reproduction evidence ONLY: that
check caused three last-node regressions and must not replace the corrected
product source. The measured roots never hit that last-node win boundary; time
results still belong to the exact measured source, not a promised future speed.

To inspect exact data using ordinary Python:

```python
from zipfile import ZipFile
import json
with ZipFile('docs/research/data/search_windows_20261022/measurements.zip') as z:
    panel = json.loads(z.read('staged-utility/analysis.json'))
    inputs = json.loads(z.read('staged-utility/inputs.json'))
```

Replay canonical records with the existing GameSession/strict serializer and
Core; source/inputs do not require a new solver, learner, worker or framework.
Archive validation used the same authoritative Core, not an independent rules
engine. All private originals remain ignored locally; no Git history rewrite.
