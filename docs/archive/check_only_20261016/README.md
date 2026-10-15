# Retained check-only / TT evidence

The manifest seals every retained member and its SHA-256. Old capsules remain
unchanged. Read the detailed research report and collaboration log at the same
Git revision before interpreting these development results.

- source/: normal GenericChess Python/C/H source and existing project scripts.
- research/: frozen input laws, full input/rule/game records, retained query and
  game receipts, all negative/UNKNOWN outcomes, literal diagnostics and producers.
- variants/: complete private check-only and lookup-tag C/H sources.
- research/source-diffs/: complete reviewable unified C patches.
- research/local-failures.json: failures, corrected guards and the explicit
  three-overwritten-preliminary-aux-receipt gap. Do not call the archive a record
  of every actual preliminary execution.
- research/consumer.py: self-contained, search-disabled full-state/history reader.
  Historical producer imports refer to prior pinned capsules; they are provenance,
  not automatic rerun instructions or license to resume an old experiment cap.

Extract to a fresh directory. From extracted source/ build the normal Native
extension with Python3.12-compatible headers/library and Zig0.16 (Windows x64):
use scripts/build_native_zig.py or the explicit build command in the published
public_copy_replay.py provenance. Then run Python with -S:
  python -S ../research/consumer.py ../research

The actual publication replay uses the existing host Python3.12.14/Zig0.16,
asserts source/module origins, verifies all member hashes/CRC, builds ONLY the
normal extension and replays the saved receipts with search entrypoints disabled.
It does not rerun Native queries/games/proofs, rebuild private variants or prove
all-domain rules/WDL equivalence. publication-replay.json records that execution
after the immutable ZIP is sealed.

No binary, credential, raw Slack/account original or private user path is
published. Project-only technical inputs/results are included regardless origin.
All result/feature fields are preserved. Each TT game journal decodes exactly to
its final row list. Costs distinguish game/batch/preparation and ordinary shared
host load. Requested TT16MiB allocates11MiB. Counts include35actual Core search
receipts among the retained query/phase records.
