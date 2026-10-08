# Repository layout and recovery

| Location | Purpose | Normal use |
|---|---|---|
| generic_chess/ | Product rules/Core/search/CLI/UI/native and supported learning APIs | Imports and product changes |
| scripts/ | Small retained development entries and tested dependency closure | chess_development.py for auxiliary games; unfamiliar_search.py for generated-rule search; old audit helpers only where a live caller needs them |
| tools/local_agent/ | Current local execution, session, Slack and Git workflow | generic-chess-local.cmd |
| tests/product/ | Fresh product semantic/search/API regressions | Default pytest |
| tests/development/ | Current evaluator/comparison regressions | Default pytest |
| tests/workflow/ | Session/consultation/stop behavior | Default pytest |
| tests/specification/ | Explicit native semantic contracts | Default pytest; limitations remain visible |
| tests/fixtures/ and root test helpers | Shared regression inputs/support | Not historical experiment runners |
| docs/research/LOCAL_MAINLINE.md | Compact current scientific direction | Read with memo |
| docs/research/CHESS_DEVELOPMENT.md | Current runnable comparison and scoped results | Execute, compare, then inspect linked raw evidence as needed |
| docs/research/data/ | Retained current results and actual runtime/regression inputs | Immutable conditions/data; never infer unexposed holdout status |
| docs/archive/ | History indexes and existing verified source/raw packages | On-demand recovery, not a backlog or executable import route |
| .local_agent/ | Ignored machine state, stop flags, memo, inbox, binaries and current pilots | Private local continuation; not portable delivery |

Do not add another workflow policy to README or a historical result. AGENTS.md,
manual and Slack manual own active rules. Old package features are not deleted
merely because current research does not use them; their product regressions stay.
Real semantic/stop/delivery/atomicity guards remain. Unused legacy cleanup approval,
resource-limit and old flow entry tools were retired, rather than rewritten into a
new defensive framework. External-checkout learning tests are no longer collected.

```powershell
.venv/Scripts/python.exe -m pytest -p no:cacheprovider
.venv/Scripts/python.exe -m scripts.chess_development --help
```

Historical scripts, tests, notes and generated outputs have exact original paths
and hashes in [cleanup archive](../archive/repository_cleanup_20261007/README.md).
Restore only needed files into a separate temporary investigation directory;
never overlay the live checkout wholesale. Current binary/source pins and active
pilot paths remain stable while their declared comparison is unfinished.

The installed-Zig Native builder scripts/build_native_zig.py was restored alone
when a demonstrated semantic import fix required rebuilding. Original source,
binary/source/compiler pins and recovery controls are isolated in
../archive/semantic_root_recovery_20261008/. No retired audit/flow entry is active.
Service/context sensitivity sources and partials have a separate purpose archive,
../archive/service_context_sensitivity_20261008/; neither archive is a live import.
