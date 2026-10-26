# Prospective pure-Leap geometry / component evidence

All data are development/exposed. No newPlayer, solver or game.
Read ../../LEAPER_PROSPECTIVE_GEOMETRY_20261026.md for claims and limitations.

- plan.json is an LF reading copy of the frozen census plan.
  Its original exact bytes (hash c06176e9...) are in json-originals.json.gz.
  delivery-plan.json revises the whole delivery forecast90->105, cap110 unchanged.
  plan-recovery-note records a transient forecast-edit mistake and exact hash-verified restoration.
- census/ retains original21780raw masks, including the v1coloring defect.
  derived-corrected/ derives corrected fields from those SAME masks.
- joint-group and sampling-weights are independently checked combinatorial derivations.
  They are not games, WDL, actualgenerator probabilities or game-sample ESS.
- literal-catalog/ has36closed recording failures. Fullinput/rootrecords retained;
  zero completefrontiers. Its original COMPLETE_FROZEN_CATALOG means attempted
  scheduling, not successfulqualification. Source-only upperbounds are separate
  in literal-catalog-source-analysis; noCore rerun filled these slots.
- relation/order/evaluator components bind limited actualinputs/returns.
  FinalPlayer choice, realdeadline behavior, wholecost/strength remainUNKNOWN.
- source-versions.json.gz preserves executed v1sources and current sources.
  Match per-phase source hashes; current corrected producers are not evidence
  that failedold slots ran successfully. The one stdin encoding step has no
  standalone pre-execution sourcehash; fullinputs/results/recipe are retained.
- work-ledger/quality-review/accepted-finish record3935.110645effective seconds
  across14intervals; administrative gaps not credited. Full source-only adoption
  and rawSlackaccount originals stayprivate.

Recheck saved data only, withoutrunning engine/Player/source capsules:

    .venv/Scripts/python.exe -m scripts.verify_leaper_prospective_geometry --data docs/research/data/leaper_prospective_geometry_20261026 --output .local_agent/FRESH-review.json

Do not execute a frozen producer to refill failedslots.31 relevant regressions
passed beforepublication; publish runs the required release gate again.
Manifest hashes bind current published file bytes. JSON reading copies use LF;
json-originals.json.gz retains the exact original JSON bytes as base64 with SHA256.
Per-phase plan hashes refer to those originals, not the LF reading copies.
