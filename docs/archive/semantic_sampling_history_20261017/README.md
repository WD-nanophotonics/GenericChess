# Complete-source replay capsule: semantic sampling/history boundaries

Source baseline9492 plus the delivered Core history predicate and tests. All
source/ members match the checked normal files; no binary, raw Slack/account
wrapper, receipt, password or credential is included. manifest.json records every
member hash. Traceback machine paths were replaced only in publication copies;
private originals and their hashes remain. The three-file prototype overlay is
UNACTIVATED; do not copy it into the product as an installation step.

Extract to a fresh directory. source/ contains the normal package, Native C,
build script,136test targets and local CLI dependencies. Use a compatible Python,
pytest and the existing Zig compiler; set ZIG to its installed path, then run:

    python scripts/build_native_zig.py
    python -m pytest -q tests/product/test_repeated_cycle_aux_defaults.py tests/product/test_search_path_runtime.py tests/product/test_generic_no_progress_draw.py tests/product/test_native_actor_effect_binding.py tests/workflow/test_local_agent_atomic_state.py tests/workflow/test_local_agent_session.py -p no:cacheprovider --basetemp .local_agent/replay-pytest

Copy studies/ to source/.local_agent/ retaining folder names. The sampling reader
requires only acquisitions/prefixes and its completed result/query files; it bans
search and reconstructs full Native/Core children/PVs. Run from source/:

    python .local_agent/semantic-sampling-20261017/reader.py

The feature control reads local stop files; for an isolated offline replay create
rollout/advisor/slack JSON snapshots in this extracted .local_agent using the
observed stop booleans. This does not modify or resume any real Agent. The Agent's
actual qualification runner separately monitored live project stops. The original
producers are supplied for provenance; do not rerun a frozen study and replace
its stored outcome or call it original-clock reproduction.

To inspect the PRIVATE prototype separately, create a disposable source copy and
apply prototype_v2_overlay/ there. Its controls.py chooses that separate package;
it is not enabled in normal source/. Native still declines no-progress/pass.

Qualification: source-only Native rebuild;136selected tests;12851complete state
checks/12191exact arm children/588PV/288caller receipts;72feature controls. Separate
private control source was executed too (4small callers plus real cancellation).
Two source-packaging failures are retained: missing unchanged test helper caused
7fails/129passes; later missing isolated stop snapshots prevented feature calls.
Only those dependencies were corrected; original studies/caps were not rerun.

See the repository report SEMANTIC_SAMPLING_AND_HISTORY_BOUNDARIES_20261017.md and
its data index for actual outcomes, limitations, ownership and current next step.
