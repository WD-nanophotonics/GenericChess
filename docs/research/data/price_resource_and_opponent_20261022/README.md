# Price/resource/opponent evidence — 2026-10-22

Read [the report](../../PRICE_RESOURCE_AND_OPPONENT_CONTEXT_20261022.md),
[summary](summary.json), [qualification](qualification.json) and [manifest](manifest.json).
The exact technical archive contains six CLOSED batches, complete rules/states/
histories/returns, scoped cold controls, current harness sources and 12 NEW prepared
inputs with zero Player queries. There are 288 physical games; self-role reuses
are additional views, never additional games. Continuing-policy UNKNOWN stays.

Registration and input preparation status fields are immutable pre-execution
snapshots. Results.json is authoritative for those completed batches. The separate
prospective-price-q0-next inputs remain genuinely NOT RUN.

For replay, extract measurements.zip into a NEW ignored local directory. Run from
this project with its normal dependencies:

    .venv\Scripts\python.exe -X utf8 docs/research/data/price_resource_and_opponent_20261022/verify.py <extracted-root>

The reader does not generate rules, query Players or rerun fitness. It reconstructs
full Core histories, literal PVs, actual node/q configurations and FLOOR RNG.
Private qualification ran five unchanged public batches, then only the new adjacent
batch. The source helper copies contain the exact imported exports; unrelated old
audit entrypoints are omitted. Producer sources retain registered paths and refuse
existing results; choose a fresh output location before any deliberate reproduction.

A public replay is shared-Core qualification, not an independent engine or proof
of all q values, perfect-play WDL, population strength or a default choice.
Original private evidence remains. No raw Slack/account/credential data is shipped.
