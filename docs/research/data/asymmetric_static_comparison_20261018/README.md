# Public evidence copy: asymmetric free-rule static comparison

Task `DEEPSEEK-SHARED-ASYMMETRIC-STATIC-20261018`.
Historical execution labels: AGENT_ID=PRIMARY_SANDBOX,
EXECUTOR_ID=PRIMARY_SANDBOX_DEEPSEEK (the pre-role-split shared DeepSeek
executor). Owner of this copy: **DEEPSEEK_AUX**, branch `codex/deepseek-aux`.
Report: `docs/research/ASYMMETRIC_FREE_RULE_STATIC_COMPARISON_20261018.md`.
Source: commit `4c665474c176bbb84a32169a540ffbe1521bc6bf` on 2026-10-18.

The run predates the current role split, so the `PRIMARY_*` labels record where
it executed, not that PRIMARY authored or adopted its conclusions. This copy is
auxiliary work checked by DEEPSEEK_AUX. The frozen inputs, outcomes and their
hashes were not regenerated during migration.

This directory is a publication COPY of the actual technical inputs, readers and
result files behind that report. The private originals (runtime logs, Slack
records, session receipts, the full test log) stay in the Git-ignored
`.local_agent/asymmetric-static-20261018/` and are not needed here.

## What is here

- Frozen inputs (hashed before any outcome): `plan.json`, `rules.json`,
  `models.json`, `roots.json`, `slots.json`, `producer-source.json`,
  `result.json`.
- Raw producer logs: `queries.jsonl.gz` and `games.jsonl.gz`. Both were gzipped
  deterministically (`gzip.compress(data, compresslevel=6, mtime=0)`); the
  decompressed bytes are identical to the private originals.
- Readers: `producer.py`, `asymmetry.py`, `describe.py`, `analyze.py`,
  `bounds_check.py`, `owner_mirror_check.py`, `owner_duplicate_check.py`,
  `score_margin.py`, `score_margin_check.py`, `score_probe.py`, `probe.py`,
  `owner_role_influence.py`, `score_outcome_link.py`, `resolution_and_cost.py`,
  `mde_power.py`, `paired_mean_crosscheck.py`, `report_consistency_check.py`.
- Derived results: `asymmetry.json`, `describe.json`, `analysis.json`,
  `score_margin.json`, `owner_role_influence.json`, `score_outcome_link.json`,
  `resolution_and_cost.json`, `mde_power.json`, `paired_mean_crosscheck.json`,
  `owner_mirror_check.json`.
- Pre-fix audit snapshots named by the report: `analysis-before-count-fix.json`
  and `score_margin-before-cluster-fix.json`, byte-identical to the private
  originals.
- Check logs: `report_consistency_check.log`, `owner_mirror_check.log`,
  `bounds_check.log`, `mde_power.log`, `owner_duplicate_check.log`,
  `determinism-check.log`, `quantile-check.log`,
  `variance-decomposition.log`.

## Frozen hashes (SHA-256, upper case)

| file | sha256 |
|---|---|
| plan.json | `AE935CEFCD772BC7A43645CA6157C557D50CCDBAF8E7D91127C0C4D5E5A97E14` |
| rules.json | `CADB7F4899FBBB8A8D6730B7B2BF2BC29783CF65F457D01185BF4CC1F3BBC02D` |
| models.json | `77346B06ECB7FD5AF170BFF9A111BFA8E0D86263479A65007CACB90213A9C5CF` |
| roots.json | `D82884C8DF1FECAABF72BA3D824C0DE8A9E56F5561F6DA91D5E44E0F16C0A891` |
| slots.json | `24713DBBBF3B0E412D2C3B2F3E3DAA5BBCE6CFC8DB7B1C54BDC05855157AF99E` |
| result.json | `AA0B2AED4ADB9EEDC29FF76AF4B445C3E4E2692B53709A4E76AD47E7CD2FE3DF` |
| queries.jsonl (decompressed) | `B976445442E0B037521ED0BA55E24657E265EE3E300C07069BCD588D95D8A984` |
| games.jsonl (decompressed) | `B220C69B994A8CA1CE713E871AE3B6E0E242A53A0079BC7675BAC739E98E05EE` |
| queries.jsonl.gz | `255A5135BAA7EAB035E9A4A06249F2E6A9DE12FC839671916F34376379028CBC` |
| games.jsonl.gz | `77ED5A85DD65C0FE63BC48702F7EEE187E428B34E8A2BC161062EFAC0196F88E` |
| analysis-before-count-fix.json | `98122ABA6BBA90385A69A6C8C31F31108DD182C25388BA4A07B3D9BEAADFB0AA` |
| score_margin-before-cluster-fix.json | `47169DB671549D6254CDF784DA3688653FE8FA8164D64B37BB060184AC54BE1D` |

`producer-source.json` records the producer/plan/rules/models/roots hashes that
were fixed before the games ran, and `report_consistency_check.py` re-asserts
them.

## Reproduction

**1. Consistency check (no reconstruction).** `report_consistency_check.py`
locates the report under the enclosing repository root and runs in place:

```powershell
& .venv/Scripts/python.exe docs/research/data/asymmetric_static_comparison_20261018/report_consistency_check.py
```

Expected: `"status": "PASS"` with **14 report/data checks**, plus
`"mainline_checks": "skipped (--mainline omitted)"` and five listed
`skipped_mainline_assertions`. Passing `--mainline <file>` to a document that
carries those wording clauses restores the 15th check. The current PRIMARY
`docs/research/LOCAL_MAINLINE.md` no longer carries that paragraph (it is
PRIMARY-owned mutable state), so the published `report_consistency_check.log`
is the 14-check run. A synthetic-fixture self-test of the `--mainline` code
path is kept in the private originals only
(`report-consistency-mainline-selftest.log`); it is not evidence about the
mainline text.

**2. Readers that hardcode the private layout.** `asymmetry.py`, `describe.py`,
`owner_duplicate_check.py`, `owner_mirror_check.py` and `resolution_and_cost.py`
read `.local_agent/asymmetric-static-20261018` relative to the working
directory. Reconstruct that layout under a fresh scratch root (never over the
private originals):

```powershell
$py = '.venv/Scripts/python.exe'
$scratch = Join-Path $env:TEMP 'gc-asym-public-20261018'
$data = Join-Path $scratch '.local_agent/asymmetric-static-20261018'
New-Item -ItemType Directory -Force -Path $data | Out-Null
Copy-Item 'docs/research/data/asymmetric_static_comparison_20261018/*' $data
Push-Location $scratch
& $py -c "import gzip,pathlib; d=pathlib.Path('.local_agent/asymmetric-static-20261018'); [d.joinpath(n).write_bytes(gzip.decompress(d.joinpath(n+'.gz').read_bytes())) for n in ('queries.jsonl','games.jsonl')]"
$env:PYTHONPATH = (Resolve-Path '<project-root>')
& $py .local_agent/asymmetric-static-20261018/asymmetry.py
& $py .local_agent/asymmetric-static-20261018/describe.py
& $py .local_agent/asymmetric-static-20261018/owner_duplicate_check.py
& $py .local_agent/asymmetric-static-20261018/owner_mirror_check.py
& $py .local_agent/asymmetric-static-20261018/bounds_check.py
Pop-Location
```

Verified on 2026-10-18 in a scratch tree: all five exit 0, and the regenerated
`asymmetry.json`, `describe.json` and `owner_mirror_check.json` are byte-identical
to the files here (SHA-256 `A290B6B7...`, `D3F48814...`, `8CF93D9E...`).
`analyze.py` also reruns on the free6 files (it rewrites `analysis.json`, whose
wall-time fields are not byte-stable). The project source is needed on
`PYTHONPATH` for `generic_chess` / `tools` imports. Scripts that import
`score_margin.build_pairs` (`score_margin.py`, `paired_mean_crosscheck.py`,
`mde_power.py`, `resolution_and_cost.py`, `owner_role_influence.py`,
`score_outcome_link.py`) additionally read the classic4 raw logs from
`.local_agent/mature-static-20261017/`, which are not in Public Git; their
classic4 aggregates are therefore summary-only here, as noted below. The full
command list and numeric rewrites are in the report's "Reproduction commands"
section. No command reruns the producer or regenerates a frozen outcome.

## Scope and honest limits of this projection

- The six free rules (`281001..281006`) are fully recomputable here: no
  fallbacks, 1344 physical / 1536 logical cells, 59,650 queries,
  20,334,363 depth-2 nodes, 0 fallbacks.
- The classic4 rows quoted in the report (271001..271004) come from the
  previously published mature-static dataset. Its rule dicts are pinned in
  Public Git at `docs/research/data/aux89_native_candidates_20261017/rule-27100*.json`
  (verified JSON-equal to the private originals), but its raw `games.jsonl` /
  `queries.jsonl` are **not** in Public Git. The classic4 aggregates here
  (`score_margin.json`, `score_outcome_link.json`, `resolution_and_cost.json`,
  `mde_power.json`) are therefore summary-only from this directory: they can be
  read, but not recomputed from raw without restoring that private dataset.
- `producer.py` refuses to overwrite frozen rules/outcomes by design; no
  regeneration is expected or claimed.
- No personal information, credentials or keys are included. Paths are project
  paths only; one absolute local path in `mde_power.log` was replaced with the
  equivalent project-relative path for publication (the private original is
  unchanged).

