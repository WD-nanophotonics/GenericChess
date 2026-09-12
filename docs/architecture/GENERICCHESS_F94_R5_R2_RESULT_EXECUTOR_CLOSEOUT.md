# F94-R5-R2 horizon-aware RESULT executor closeout

`scripts/f94_r5_result_executor.py` is the separate fail-closed consumer for
the frozen R5-R1 v2 PREP.  It validates PREP bytes, schemas, protocol/source
commit, committed qualification authority hash, candidate/corpus identities,
and every nested PREP fingerprint before native compilation or Arena.

The boundary exits before native compilation/Arena with zero compute.  Ready
controls are wired exclusively through `measure_strength_response`; the
executor has no duplicate depth, horizon, or strength reducer.  Its completion
contract is exactly 18 Arena invocations, 108 pairs, 216 games, and 216 traces
across the two ready controls, with 36 strongest-vs-weakest games per control.

Focused tests inject a fake runner to prove the execution shape and no actual
Arena/Heavy task was started.  This checkpoint only creates execution
authority.  A real RESULT still requires the separately approved compute plan,
resource envelope, and Supervisor binding for the exact sandbox SHA.
