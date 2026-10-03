# Freeze finite reference and post-capture diagnostic corpus before values

Base 52571007d06d58a2e7b9ef532ab720b5037c7d4d. Use the unchanged
POST_CAPTURE_VALIDATION_CONTRACT.md criterion and actual-inventory Q proposal.
This is a small, reproducible finite pilot, not a precise population estimator
or a material-value formula already shown useful. Human values stay sealed.

Generate FOUR accepted reference boards per game, equal mass 1/4, using seeds
Chess 202610040101 and Shogi 202610040102. Retain actual inventory, owner 0
turn, empty hands and synthetic state exactly as Q. At most 128 raw proposals
per game in total; no type-specific sampling or success-based selection.

Generate ONE independent post-capture child per initial ordinary victim type,
equal mass 1/5 Chess and 1/7 Shogi. Types are sorted compiler-derived initial
own non-anchor types. Per-type seeds are 202610040201+i Chess and
202610040301+i Shogi, where i is the zero-based sorted type index. Each stratum
allows at most 128 raw proposals. Draw a fresh whole Q board, reset parent to
owner 1, exhaust the legal captures of that victim type, retain only ongoing
children, fail on ambiguous duplicate physical capture identity, and uniformly
choose among the complete candidates. Reject whole parents with no candidate.
This conditions parent support, then chooses a capture; it does NOT sample all
capture pairs uniformly, which would bias toward high-capture parents.

Require complete reference counts and all 12 deployment strata, exact own
board inventory delta -e_t, preserved actual child history/aux/check/hands,
no own hand tokens, and no reference/deployment-parent overlap. Overlap fails
this frozen run, never triggers adaptive replacement. Preserve every accepted
reference/parent/child, seed and per-reason proposal counters. Do not read Y or
compute v when generating. A missing stratum is incomplete, not a type score0.

Generation gate: one process, 5,000 capture materializations and 25 seconds
total including compilation, with no higher-budget retries or new seeds. Save
partial corpus/accounting on proposal exhaustion. Time/transition aborts provide
no complete corpus. Successful generation only establishes coverage/cost.

Only after corpus bytes/hashes and generator are frozen may a separate labelled
pilot run: complete all board actors/replies on eight reference roots, then
freeze raw v_t=(1/4)*sum_reference S_t/n_t and reference-only constant. Afterwards
label the 12 deployment roots, without changing state, weights or formulas.
Each game is evaluated separately against BOTH zero and frozen constant
baselines under the 10% margin. All-zero reference is unusable for this finite
construction, not proof of zero true population means. Zero baseline risk or
incomplete coverage cannot pass. Do not expose deployment labels earlier or
fit to them. Labels need a separate runner with these already frozen roots.

Labelled pilot gate, declared now before values: at most 20 roots,
60,000 materializations / 30 seconds TOTAL, one process, exact complete replies;
no truncation, hidden draws, partial score0 or budget increase. On signal/gate
failure retain evidence and reconsider the independently motivated model/cost
premise instead of enlarging this sample. A finite pass supports only this
balanced corpus, not a population error claim, Shogi own-hand/promoted values,
strategic/WDL utility or the project's material benchmark. Next material use
would require its distinct frozen validation; Xiangqi references remain sealed.
