# Learning route support evidence - 2026-10-17

Read the purpose report and data/learning_route_core_support_20261017.json.
This archive contains PRIMARY observations/plans/scripts, both new fixed-policy
D2/D3 game journals, exact published AUX86 dependency source and recorded data,
and the prior exposed Core input records needed by the observations.

Base product is96b96b830e70e4a15a5ca8a24006e21075fc884c. AUX dependency is
5f3cc0aada9f75794a55f12119f1e78e59039142; these files are copied from its
verified380-payload capsule, never from an active AUX checkout. No new learner,
training checkpoint, production change or generic-strength claim is delivered.

Extract to a disposable copy of that base checkout, preserving relative paths.
Use the project's Python/chess dependency. audit-fixed-depth.py replays128new
records and recomputes bounds; aux86-independent-verify.py runs13published tests
and replays64old records. These audit scripts write only their private outputs.
The37episode frozen-search replay and64failed-root diagnostic have original
plans/closed receipts and scripts. Do not rerun a producer into its existing
output directory or present a new execution as its original frozen study.
The historical training run.py/evaluate.py files are dependencies, not commands
to launch another learner. Final fixed-policy runner uses a process-local atomic
JSON endpoint shim only; model/search/adapter sources were unchanged.

All128planned slots were visited:64D2actual terminals and64D3SEARCH_LIMIT_UNKNOWN.
The D3budget is deliberately not increased. All64same-limit diagnostic queries
hit4096nodes. Learned-vs-initial gains atD2are.0625/.75 on8shared families; the
first exploratory interval crosses0. Same families acrossseeds are not extra
independent observations. Training receipt reproduction matches5299actions/node
counts and37forward TD updates; it is same-source, not independent training.

Manifest records both original and publication-copy hashes, plus ZIPCRC verified.
Only publication copies sanitize local home/project paths and machine identity.
Private raw Slack/account originals and copyrighted papers are excluded. Source
URLs and concise own findings remain in the report; no paper text is distributed.
