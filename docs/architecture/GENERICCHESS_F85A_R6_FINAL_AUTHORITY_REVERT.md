# GenericChess F85A-R6 Final Authority Revert

F85A-R6 restores the final accepted F85A-R4 authority after the R5 geometry
rewrite was rejected by the higher-authority workflow review. This is a strict
zero-compute corrective: no lane experiment, Heavy run, teacher call,
36-root acquisition, C2 fit, Arena, root resampling, or production semantic
change was performed.

## Exact restoration

The following tracked files are restored byte-for-byte to the accepted R4
checkpoint `b45ed13fe8cd8498ef4ebd2019757011825727bb`:

- `artifacts/f85_c2_train_teacher_evidence/train_precompute_manifest.json`;
- `scripts/f85_c2_train_teacher_acquisition.py`;
- `tests/test_f85_c2_train_teacher_acquisition.py`.

The manifest is again bound to Git blob
`f0afca1fc1979a692a841f3fcb25da10a8e6d482`, derived manifest SHA
`68874208804b920e23484db774d265f5880c9be73a91fa61d9ea53c9a76c73fa`, and
`max_concurrent_roots = 2`. Runtime validation, batch width, default fake plan,
and first-batch terminal tests all require two lanes; three- and four-lane
plans are rejected before any teacher runner starts.

R3 and R5 remain historical diagnostic records only. Their smoke measurements
do not supersede the accepted full-contract F84 two-lane calibration, and no
further lane experiment is authorized.

## Final classification

`C2_TRAIN_TEACHER_ACQUISITION_HARNESS_READY_FOR_LARGE_APPROVAL`

The only next action is review of an exact two-lane large-compute tuple. No
teacher acquisition may begin until Chat scientific approval and registered
Supervisor approval bind that same immutable tuple.
