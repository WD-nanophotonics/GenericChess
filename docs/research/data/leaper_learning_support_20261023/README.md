# Learning and mating-support evidence

Read the [purpose report](../../LEAPER_LEARNING_AND_MATING_SUPPORT_20261023.md).
This is DEV_AUX truth/learning work using committed sandbox
`06c7eb414b0ec8993f5d3d90606e8fcba36ff9d7`. It generates no PRIMARY fitness games
and changes no production defaults. Raw large natural graphs stay ignored.

`evidence.json.gz` is 2,199,061 bytes, SHA256
`96664fd4a0a0444bf147240f105e1908139b50212d200a36cbff88fd9a192a75`.
It contains the 16-episode exposure cohort, 304 additional pilot episodes,
models/receipts/full records, 36 compact solved KX certificates, all 75
orbit-inclusion comparisons, four literal argmax cases, the capped new 5×5
observer and its separate positive Session certificates. Source strings are
inert provenance data; the reader never executes or unpacks them.

From the repository root:

```powershell
.\.venv\Scripts\python.exe docs/research/data/leaper_learning_support_20261023/verify.py
```

The actual sealed reader passed in 233.153s. It checks all 320 episode histories,
17,263 literal PV edges and all 256 TD updates with independent arithmetic;
all 428,568 support vertices/2,181,248 edges against actual Core and independent
Bellman/rank conditions; all inclusion counts and four argmax cases; four
positive Session certificates; and both cooperative extensions. Core is shared,
not an independent rules engine. The 1,793 natural four-actor graph labels get
full-root/action binding checks only, not independent WDL certification. Their
large underlying graphs, including three partial graphs, remain local; their
hash/size receipts and actual executed source are retained in the packet.

KX certificates cover complete constructed fresh legal placements with one
ordinary type, not opening reachability or arbitrary histories. Decisive ranks
fit inside clock 128; draw safety survives repetition-four/clock draws. A missing
or capped observation is never inserted as a draw. Costs/vertices summed across
components include repeated lower-material states and partial work.

`loss_entry.json.gz` is 4,173 bytes, SHA256
`a1963e00c4cf7eab9f27f3df1b4ebf520b7f635131cf34adb92a87fe0e503377`.
It separately carries the one-edge lifted ply-39 WIN certificate, the NEW
ply-38 five-actor probe (both targets UNKNOWN at 30k nodes each), and the literal
<=4-ply controls on all six formerly unlabelled roots. This neither resumes the
closed graph/proof caps nor promotes the selected histories into training data.
Ranks in positive proof trees are upper bounds, not minimum mate distances.

The existing Session API independently reads/verifies the serialized lift:

```python
import gzip, json
from pathlib import Path
from scripts.leaper_design import compile_rule, ruleset_from_dict
from scripts.generic_session_certificate_json import decode_session_certificate
from scripts.generic_session_win_proof import verify_session_certificate

base = Path('docs/research/data/leaper_learning_support_20261023')
p = json.loads(gzip.decompress((base/'evidence.json.gz').read_bytes()))
s = json.loads(gzip.decompress((base/'loss_entry.json.gz').read_bytes()))
raw = s['lift']['certificate']
c = compile_rule(ruleset_from_dict(p['rules'][raw['ruleset_fingerprint']]))
session, certificate = decode_session_certificate(c, raw, max_nodes=30000)
assert verify_session_certificate(session, certificate,
    max_nodes=30000, seconds=30)['verified']
```

The main reader initially failed after support checks on a sparse zero-count
dictionary key. Its `.get(..., 0)` repair and failed log are retained; no
experiment, model, frozen slot or cap was rerun to repair a reader.
