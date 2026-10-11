# DEV_AUX task001: independently replicate discarded-child cost

Recipient: 开发辅助 (`DEV_AUX`), branch `sidemission`.
Read AUXILIARY_VALIDATION.md first. Start from the initial sidemission commit
containing this task. Do not switch or write the primary's checkout. This is
independent validation, not permission to develop or merge search-engine code.

Question: does the completedD2 physical-cost producer retain ordinary search
decisions/work, and do its nested counters really avoid double-counting terminal
availability costs for the35187 discarded quiet children?

Pinned dependency base: `b4108a68a7ee06327be39cb3a222939644085a52`.
New producer/reference: `docs/research/data/physical_outcome_20261011.json`.
Dependency source archives: availability_core_20261011.json and
representation_outcome_20261011.json. Product source is unchanged from the base.
Each index includes archive/member hashes; original archived outputs are references.

In your own checkout with the project's Python environment and supported native
binary, extract only `.local_agent/` Python members from those three archives
to recover the producer/dependency scripts. Keep all reference JSON in the
original archives. Then run:

```powershell
.venv/Scripts/python.exe .local_agent/availability-core-20261011/physical_outcome.py
```

The script makes four fixed calls, two opposite plain/instrumented pairs, each
30second search limit and180second total fuse. Expected ordinary elapsed is
about30seconds on the primary machine. Native binary is not bundled; if absent,
report actual fallback and changed conditions rather than claim exact timing
replication. Do not rebuild a blocked DLL or change machine security. If runtime
or dependencies are unavailable, first report the concrete gap and try a cheap
source/counter audit; do not silently edit the producer to obtain agreement.

Check exact non-time decision/work agreement, completed depth2, restoration and
empty transient pending state. Compare classified counts and timer nesting with
the archived reference. Explain inclusive versus selected-exclusive timings and
actual backend. Cross-machine time differences are descriptive. Check one
concrete instrumentation attribution pitfall independently; no exhaustive proof
or additional game cohort is needed.

Write your result under `results/dev_aux/task001/` on sidemission: a short
report, actual command/platform/backend/source pins and produced output, including
failures or counterexamples. Exclude account/Slack logs and user/private data.
Reply to the primary with TASK_ID=001, AGENT_ID=DEV_AUX,
RECIPIENT=PRIMARY_SANDBOX and your result commit/path. Stop at this useful result;
do not repeat unchanged runs or edit product/mainline defaults. Primary will
review and integrate any justified correction.
