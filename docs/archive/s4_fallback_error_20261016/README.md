# Required Native errors and bounded follow-on evidence

This is a standalone scoped source/evidence capsule. `manifest.json` records
all member SHA256/byte lengths and the ZIP SHA256. Check every member and CRC,
reject absolute/traversal paths, then extract into a fresh project-owned folder.
Measured sizes are in the manifest; do not silently truncate any result arrays.
No private Slack/account output, credentials or Native binary is included.

From the restored `source` directory, using the existing project Python/Zig:

    python scripts/build_native_zig.py
    python ../consumer.py ..
    python -m pytest tests/development/test_native_internal_error.py tests/development/test_native_dynamic_feature_error.py tests/product/test_native_cancellation.py tests/product/test_native_semantic_qsearch.py tests/product/test_native_pending_continuation.py tests/product/test_native_legality_terminal_boundary.py tests/product/test_native_capacity_result_features.py tests/product/test_native_rule_horizon_capacity.py

The build uses an already installed Zig (set ZIG if needed); no new tool/service,
worker or download is required. Use a writable fresh pytest basetemp/cache.
The consumer asserts this restored Native image is loaded and DISABLES every
search entry before complete record/state/PV/field checks. It does not reproduce
old cancellation timing, fault occurrence, optimal minimax or another Agent's work.

`source` is the final product and affected-test closure. `provenance` holds exact
as-executed producer scripts and private C overrides, with distinct baseline,
timer, rejected SHA-staging and isolated mixed-leaf tiers. Historical producers
may name private output/dependency paths; they are provenance, not automatic rerun
recipes. The complete C overrides plus source closure suffice to rebuild those
images with the normal compiler command, without the old checkout. None of the
prototype overrides is an installed product change. Fault hooks exist only in
the development fixture/private provenance, never in product runtime.

`research` keeps successful, failed and budget-censored controls, full arrays,
actual record histories and original plan caps. Imported S4 Positions are clearly
separate from played game records. Original v1 restored-test fixture failure and
a diagnostic recorder variable error are retained as structured evidence; the
private originals remain untouched. Sanitizing publication copies does not alter
any scientific score, missing slot, action or stop reason.
