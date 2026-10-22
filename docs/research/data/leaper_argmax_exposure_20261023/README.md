# Selected argmax/exposure evidence

See [the report](../../LEAPER_ARGMAX_EXPOSURE_20261023.md).

`manifest.json` pins the compressed bytes, frozen PRIMARY inputs, measured and
closing infrastructure revisions, coverage and closed effective-work intervals.
`evidence.json.gz` contains selected full histories, all diagnostic query/cost
joins, exact argmax controls, short-mate/WIN certificates, clock controls,
actual executed producer sources and the zero-update episode. Raw graph caches
and full PRIMARY trajectories are not duplicated here.

From the repository root, using its normal Python/native dependencies:

```console
python docs/research/data/leaper_argmax_exposure_20261023/verify.py
```

The reader reproduces selected literal Core searches, full queried-history
bindings, saved certificates, clocks, PVs and compact arithmetic. It does not
rebuild the capped graph census or supply an independent rules engine.
`verification.json` is the actual sealed-reader result. Earlier failed
bootstrap/order descriptions and missing slots remain explicit in the packet;
no closed cap is reopened by verification. Source texts are evidence, not an
instruction to execute arbitrary archived producers.
