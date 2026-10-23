# Budget calibration / cost / price-horizon evidence

Read[the report](../../LEAPER_BUDGET_CALIBRATION_AND_COST_20261023.md).
Complete rules, profiles, histories, planned slots, actual decisions and costs
are retained. Source capsules are inert DATA, never automatically execute them.

| Packet | Physical deployments | Gameplay returns | NEWpreflight calls | UNKNOWN |
|---|---:|---:|---:|---:|
| three-cell |36|1030|24|0|
| alignment |96|2128|48|0|
| prospective |576|19734|352|0|
| price-horizon |16|518|6|0|

724physicaldeployments include48terminal prefixes and676played continuations;
475literal final records are not IID. Four separate diagnostic root returns are
in the supplement, not extra games or preflight calls. SharedCore qualification
is not independent WDL, uniform leaf-horizon proof or binary attestation.

Each manifest binds actual compressed/decoded bytes. Each qualification file is
the ONE full public-copy history/PV reader receipt; qualification-summary binds
actual local originals/sources/controller histories and cost/diagnostic PVs.
The supplement contains late costs, matched predictions, price witnesses and a
24input0query next proposal. It is NOT_RUN_READY. Private raw Slack/session/HTTP
originals are not published here. Ordinary sources and their tested replication
entry are tracked separately; source-publication-provenance explains byte versions.

## Reproduction without source-capsule execution

At the pinned repository source, use a NEW ignored output directory. First copy
only input DATA into a new replication. This command performs0Playercalls:

```powershell
python -m scripts.leaper_calibration_run --materialize-from-packet docs/research/data/leaper_calibration_20261023/price-horizon.json.gz --group price-horizon --output .local_agent/reproduce-price-horizon-NEW
```

It retains replication-original-registration.json. Reencoded JSON has a NEW
byte hash despite equal decoded values; new registration records that hash,
actual new preparation time/source, packet SHA and original provenance. Logical
policies/slots/caps are retained. Existing frozen originals are never overwritten.
The library source hash must match; a mismatch is a stop, not an expected-value fix.
The original empirical forecast remains an OLD planning estimate; execution makes
NEWfull-historycost calls. Then, only when deliberately reproducing computation:

```powershell
python -m scripts.leaper_calibration_run --output .local_agent/reproduce-price-horizon-NEW
python -m scripts.leaper_design qualify --output .local_agent/reproduce-price-horizon-NEW
```

The same preparation supports the three-cell,alignment,prospective packets by
changing packet/group/output. Their ordinary analysis commands are:

```powershell
python -m scripts.leaper_budget_calibration analyze --output <NEW-three-cell-directory>
python -m scripts.leaper_opponent_alignment analyze --output <NEW-alignment-directory>
python -m scripts.leaper_role_budget_prospective analyze --output <NEW-prospective-directory>
python -m scripts.leaper_budget_cost_diagnostics --output <CLOSED-directory>
python -m scripts.leaper_first_root_diagnostics --output <CLOSED-three-cell-directory>
python -m scripts.leaper_expected_cost_mixture --output <CLOSED-three-cell-directory>
```

The prepare subcommands also accept full saved input JSON and source registration;
role_budget_prospective prepares its own frozen16prefixes from the12input source.
The selected price-horizon root and full canonical input are explicit in its packet.
A replay of an existing packet needs no new Player calls:
`python -m scripts.leaper_portrait --packet <packet.json.gz>`.
All delivered packets were already qualified once; unchanged replay is not a
model-switch quota or reason to refill old fitness. New source tests cover the
role/baseline interval dependence, main+qnode budget boundary, and reencoding
provenance while preserving original registrations and0query preparation.
