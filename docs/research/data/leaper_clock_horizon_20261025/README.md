# Pure-Leaper clock evidence packet

All producers CLOSED. Exact private originals stay ignored. The manifest binds
raw/original and public bytes. Gzip members are lossless; JSON without gzip is LF
presentation, with failure paths sanitized only in the identified copy.
`executed-source/*.txt.gz` are **DATA, NEVER EXECUTE**. Maintained scripts are the
readers; run no producer to fill a missing or failed slot. The repaired observer
has only zero-query tests; its failed original source remains exact here.

Labels input is the exact already-published
`../leaper_ordering_diagnosis_20261025/next-default-panel-inputs.json.gz`, pinned
by the SHA in manifest and each labelled plan. It retains full RuleSet/history,
actor/clock/frontier and fixed AUX26d414c certificate provenance. No new graph,
independent solving or human labels are implied. Pre-feature player/search source
is pinned to fbb0335c522dad79f53f4cda65d2b3b7b2a80449; the cap experiment also
archives its actual new backend sources. Source identities are not reconstructed
from the maintained observer repair.

| Directory | Meaning |
|---|---|
| observer |1 failed attempt/0returns;D1–5 exact prefix;D6/7UNKNOWN;future repair unexecuted |
| qorder |32returns/8rules;11common-depth pairs;5trivial immediate-win pairs |
| endpoint |1 fullremaining4/Q0 query;0 vs static−1106 |
| last-ply |6queries;actual activation fails to repair p53 |
| completion-proof |2queries,any-win goal;1M cap ends without reported win |
| completion-quality |32queries,20s move goal;default16/16,candidate15/16 |
| clock-cap |10new opt-in queries,reuse10paid default controls;8complete/2limited |

The feasibility pilot and20s panel have different goals. The panel is formally
post-pilot exposed falsification, not blind validation. Changed q policy need
not preserve fixed-depth score; all actual positive/negative values are retained.
Only q-order and hard-clock-cap comparisons demand their declared exact parity.
Requested clock cap is not proof that search completed it. Eight completed clock
benchmarks areDRAW; no full-rule-class/strength success is claimed.

Data-only checks from repository root (PowerShell):

```powershell
.venv\Scripts\python.exe -X utf8 -m scripts.verify_leaper_qorder_prospective --directory docs/research/data/leaper_clock_horizon_20261025/qorder
.venv\Scripts\python.exe -X utf8 -m scripts.verify_leaper_last_clock_ablation --directory docs/research/data/leaper_clock_horizon_20261025/last-ply --inputs docs/research/data/leaper_ordering_diagnosis_20261025/next-default-panel-inputs.json.gz
.venv\Scripts\python.exe -X utf8 -m scripts.verify_leaper_clock_completion --directory docs/research/data/leaper_clock_horizon_20261025/completion-quality --inputs docs/research/data/leaper_ordering_diagnosis_20261025/next-default-panel-inputs.json.gz
.venv\Scripts\python.exe -X utf8 -m scripts.verify_leaper_rule_clock_cap --directory docs/research/data/leaper_clock_horizon_20261025/clock-cap --reference docs/research/data/leaper_clock_horizon_20261025/completion-quality --inputs docs/research/data/leaper_ordering_diagnosis_20261025/next-default-panel-inputs.json.gz
```

The51 relevant unique tests include public-gzip qualification, rejection of a
changed prefix, budget/automatic-policy behavior and the real runtime-view
recording regression. Repeated publication tests do not multiply that count.
Work/session acceptance is in `session-accounting.json`; zero UTC spans are not
credited merely because perf_counter shows a nonzero short call. Timing evidence
includes concurrent-load and sequential/cold-player (not cold-process) limits.
Engineering and record/delivery overhead are not amortized by8saved queries.
