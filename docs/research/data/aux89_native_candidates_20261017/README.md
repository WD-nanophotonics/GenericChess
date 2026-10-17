# Actual AUX89 candidates for the existing semantic backend

This packet contains eight INITIAL and eight corresponding LEARNED endpoint
checkpoints from fixed PUBLIC AUX89 source63b4ce1d8f0e94755bf2102dfbd4f524a91c0264.
The source is results/dev_aux/task2525/result.json inside its exact89archive.
No coefficients were fitted, pooled across rules, median-normalized or changed.
BoardP1 is a scale convention within each rule, not a human pawn prior.

Use the existing backend from the repository root:

```powershell
.venv/Scripts/python.exe docs/research/data/aux89_native_candidates_20261017/consume.py
```

The example loads LearnableMaterialCheckpoint.from_dict, replays the included
canonical GameRecords, compiles the four ordinary generated rules for explicit
semantic execution, and invokes SemanticSearchEngine. It imports no AUX search,
learner or solver. It actually executes32frozen D2calls on16TRAIN-exposed roots,
checking scores/actions/complete state and history/parent isolation. Normal and
restored-Python-source/Python-S/explicit existing Native runs both pass32calls.
The Native extension is an external existing same-version dependency, not bundled.
This does not silently select a different engine when Native is unsupported.

Precision matters: material_scale256 is explicit, value_scale10 is unchanged.
The historical default material-only scale1 erased all eight source updates;
there are no fake zero dynamic tables just to trigger another scale. Floating
weights are exact source values; Native integer values are explicit approximations,
not exact floating predictions. The purpose report retains error bounds and all
32floating optimal sets versus quantized controls.

The checkpoint parent links connect a canonical source-initial conversion to its
source-endpoint conversion. Generation1 means ONE endpoint conversion, not an
invented PRIMARY optimizer step or complete four-episode optimizer lineage.
Source counters remain provenance; these files are not resumable AUX optimizer
state and must not be advertised as that same algorithm's continued training.
None is champion/default/promoted. UI Test and AUX's own curve remain independent.

All four rules were TRAIN-exposed; included roots are diagnostic source queries,
not new validation or unseen-rule transfer. The source128game panel has17UNKNOWN
and gain[-.25,.28125], not demonstrated Generic strength gain. New protocol,
models and data need their own declared scope; do not pick a winning seed here.
Semantic histories were actually replayed; these four source records had exactly
one matching typed binding per legacy edge. No all-domain legacy converter,
board/history coalescence, truncated auxiliary semantics or new API is supplied.


A second executable example actually plays the fixed compatibility smoke:

```powershell
.venv/Scripts/python.exe docs/research/data/aux89_native_candidates_20261017/play_smoke.py .local_agent/NEW-native-play-output
```

Pass a NEW output directory. Final source actually returns all16slots/468D2calls,
14terminal/2H64UNKNOWN,60drops/5promotions, full replay equal. It is an inference
compatibility check without initial-model controls or a strength claim. Existing
project stop flags are read, not reset. Script writes research outputs only.
