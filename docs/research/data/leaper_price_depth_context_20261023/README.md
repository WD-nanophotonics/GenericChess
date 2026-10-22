# Selected Leaper price/depth/context evidence

`evidence.json.gz` contains the 18-query capture matrix and literal argmax,
the closed 16-root natural 5×5 positive-bound preflight, and the 48-root
AB/AAB/ABC public-query, short-quality and ABC full-support diagnostics.
Only selected complete rules, full records, receipts, capped/unknown outcomes
and executed producer sources are retained here. Temporary drivers and raw
corpora stay under ignored artifacts; no additional game or training runs.
The capsule also includes the four-root, 37-price exact local-cone control.
Compressed size: 96,847 bytes. SHA256:
`d0661623e3323f3ea7898bd04566608555bb34d81c291f88637e7df396702ad4`.

`clock_tail.json.gz` is a separate post-hoc proof of the one retained censored
endpoint in PRIMARY's newer edda packet: full history, four remaining rule
plies, 1,696 Session nodes and all nine root actions DRAW. It does not fill the
original UNKNOWN game or two unstarted slots. Size 77,948 bytes; SHA256
`6cd9c5e8d4ddf476057d875a3874f5ad3fa7a092a710aa2c489a395d0290d835`.
`clock_tail_verification.json` records its separate independent Core edge and
Bellman replay, including missing-root-edge rejection.

Infrastructure: sandbox `06c7eb414b0ec8993f5d3d90606e8fcba36ff9d7`.
Capture input: sidemission `4559acd1b0b7fbc26f1aaf837f9280bd1ce48337`.
Older natural inputs, byte-identical to sandbox
`55abf3de22f20ac03eb07b5260284466173a3264`:

- `docs/research/data/resource_generation_material_20261022/observations.json.gz`
  SHA256 `6ad501cdfe22b4b59e1a33fef44519eff66e4566fecff1efa674cec9310a3cbf`.
- `docs/research/data/small_rule_family_20261022/observations.json.gz`
  SHA256 `1a48f7eaf038cc7745d6dd82ebc784d7a666286a59c7d159c4c1ba3c5338d087`.

Run from the repository root:

```powershell
.\.venv\Scripts\python.exe docs/research/data/leaper_price_depth_context_20261023/verify.py --literal-six
```

The reader replays every selected public PV and full root, checks all saved
positive WIN certificates and their root/action joins, and recomputes literal
capture and complete ABC D4 argmax. ABC D6 receives saved support-arithmetic
and action-binding checks by default; `--literal-six` additionally regenerates
its complete trees. Partial trees have no asserted support. This shares Core
and Session with production; it is not an independent rules engine.
The local-cell control is fully recomputed and its ray coverage and affine fits
are checked. One target-flipped reference certificate must be rejected.
When present, the clock-tail supplement is also checked. `verification.json`
records the complete main-capsule pass before the supplement was added; its
unchanged inputs were not recomputed merely to check the independent new tail.

The reader does not re-prove unknowns, regenerate the closed graph census,
independently reconstruct every metadata selection from the raw corpora, or
establish population, held-out, learning or speed benefits. Failed bounded
proofs are UNKNOWN. Numeric gradients and changed choices are not action WDL.
