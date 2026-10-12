# Existing search-speed evidence: backend scope

There is no directly measured current persistent Native exact-root q0 versus
python-chess/cshogi ABP interval with rules, leaf/ordering evaluation, completed
horizon and TT conditions all aligned. Do not compose one from different
algorithms, pins, budgets or historical ratios. No new benchmark was run for
this clarification, and unpublished ordering-view timings are excluded.

| Existing comparison | Chess elapsed ratio | Shogi elapsed ratio | Meaning |
|---|---:|---:|---|
| Historical identical minimal lexicalAB D2, noTT/q/PVS: GenericCore / specialized rules |10.20–21.43|30.45–182.42|Four roots per game, each reversed twice; work/score all match. Specialized is python-chess1.11.2/cshogi1.0.9. Old rules/adapters, not current C search.|
| Same D2: Native legality with Core state / specialized |6.77–10.26|24.38–66.94|Hybrid Python state/history/algorithm remains.|
| Historical identical PythonAB,4096entry cutoff: full Native-state bridge / specialized |3.74–5.92|Unavailable|Four Chess roots, reversed twice; work and trace agree; partial-depth work control, not completed current q0.|
| Recent finiteD5 persistent Native / optimized GenericCoreAB |Unavailable|CoreAB/Native2.13–2.14|One Shogi root: Native9.651/9.678s, CoreAB20.574/20.686s. Generic Core with Native legality/availability, not cshogi search.|

The last row has the same material leaf/q0/full history but different ordering
and TT resources: Native1MiB/min2 versus CoreAB250kentries, own ordering,
noPVS/root-tactical. CorePlain reaches onlyD4 under64s, so its independentD5
value remains unknown. That single root cannot provide a general speed range
or a primitive-speed attribution. The ratio denominator is stated in each row;
larger elapsed ratio means the numerator takes longer, not stronger play.

Original immutable members:
archive/search_backend_attribution_20261010/evidence.zip::aligned-d2.json and
archive/native_terminal_20261010/evidence.zip::
.local_agent/native-terminal-20261010/bridge-assay.json (paths under docs).
The first cohort covers promotion/EP/mate/drop and played/sparse roots; it is
exposed development scope, not a representative population or an Elo estimate.
Numbers were recomputed from raw matched work/trace records; source and original
hashes are bound in data/ordering_status_20261012.json. Related interpretation:
SEARCH_BACKEND_ATTRIBUTION.md and Q0_TRACE_AND_TERMINAL_POLICY.md.

Dot's2026-10-12 numerical inquiry was answered with these existing facts and the
explicit current gap. Quoted other-chat requests do not expand task authority.
No frontend, specialist-only engine replacement or new large benchmark follows.
