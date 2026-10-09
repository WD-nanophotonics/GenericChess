# Finite-search compression recovery

`index.json` and immutable `evidence.zip` preserve the original pre-training
declaration, complete D2 labels, all stopped/capped D4 records, search controls,
static baselines and prepared runner. Its PREPARED_NOT_STARTED status describes
that snapshot, not current work.

`training-index.json` and `training-supplement.zip` contain the one authorized
fixed model, unfavorable greedy results, diagnostic interventions, dense/sparse
actual callers and fresh same-rule trajectory checks. Each member has a hash.
Recover both packages into a separate checkout of the index's base commit with
a rebuilt Python environment. Never restore active operational state. Recovery
checked all supplement hashes and all228model-choice calculations without
refitting; search reruns are new measurements, not replacements for originals.

Use `docs/research/FINITE_SEARCH_COMPRESSION.md` for claims and limitations.
Raw Slack/account records, user inputs, credentials and live memo/session state
are excluded. Historical scripts include intentionally retained failures and
different output guards; do not bulk execute them or overwrite frozen records.
