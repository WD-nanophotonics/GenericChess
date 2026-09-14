# F85B-R2 Canonical Phase Provenance

This checkpoint repairs resumability for the F85 minimal teacher-row path.

## Durable behavior

`_phase_provenance()` now hashes only the immutable minimal-manifest root
record.  Worker-only `action_history` and `replay_actions` fields are excluded
from that identity, so the parent restart scan and a spawned worker derive
byte-identical provenance for the same root, plan, manifest, and C1 checkpoint.
Only `COMPLETE` phases with matching provenance remain reusable; incomplete and
`TIME_CAP` phases are still inadmissible.

The regression suite covers runtime-independent provenance, sealed-root reuse
without recomputation, and reuse of an already complete root2k phase after an
interrupted invocation.  The focused F85/F82 suite passes (27 tests).

## Exact v12 compute plan

Chat approved and the registered Supervisor bound the exact v12 plan to the
published implementation checkpoint before this report was prepared:

- implementation checkpoint: `3d0915d26dcb453d4d28ab99bc9a430bbe6b7f31`
- plan: `f85b-c2-minimal-teacher-rows-v12`
- plan SHA: `a7b99996fbda298e480d52ee47edee226ae8aefcece5d8cbbf4ae3e01f6d0a28`
- envelope SHA: `5032868cf195c3fc050e70912f20d7965e57e4260d4fbb82e2e204f903c03698`
- maximum nodes: `9,954,000`
- declared maximum selected actions: `8`
- lanes: `2` on `16` logical CPUs; per-root wall bound `900s`

No Heavy, C2 fit, or Arena was launched in this work order.  The plan is
ready for a separately authorized execution session only.
