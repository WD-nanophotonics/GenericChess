# task2636 frozen-root drop availability review

The audit rehashed the frozen task2636 study plan, root pool and candidate
index, rechecked all 14 pinned replay-runtime files and 16 candidate rule files,
replayed the already selected roots, and confirmed each reconstructed fixed-scale
feature vector equals its frozen vector. It enumerated legal actions at each
root without reading outcomes or search values and without changing any root.

| Phase | Frozen roots | Roots with a nonzero hand feature | Roots with at least one legal drop | Legal drop actions counted | Candidates with ≥1 such root |
|---|---:|---:|---:|---:|---:|
| Training | 1,920 | 1,108 (57.7%) | 588 (30.6%) | 19,465 | 16/16 |
| Evaluation | 256 | 140 (54.7%) | 83 (32.4%) | 2,781 | 16/16 |

Thus every candidate has some selected training and evaluation roots where a
drop is legal, and the frozen material vectors represent hand inventory on
many selected roots. This closes a finite root-mechanic availability question.
It does **not** show that the learner's search selected or traversed a drop,
that the drop channel received a TD update, that any game reached a terminal,
or that the panel represents the full Generic rule domain or population.
Although the rule files contain promotion masks, none of the 1,920 training or
256 evaluation roots has a legal promotion action. All16 candidate files omit
semantic actions, declarations, automatic adjudications, consecutive-action
policies, alternate setups, repeated-cycle targets, no-progress draws and
pass actions; default generic history/repetition/max-ply/stalemate handling
still applies. All candidates use `repetition_limit=4`, `max_ply=512` and
`stalemate_result=draw`; omitted `repetition_policy` and `capture_disposition`
use the engine defaults. The current panel is therefore a finite generated
movement/drop feasibility case, not a substitute for learning coverage over
full Generic rules. Descendant promotion exposure, auxiliary-state mechanics
and actual training/evaluation remain separate questions. Keep the root pool,
channel order, costs and interpretation unchanged.

Candidate-level support is heterogeneous despite 16/16 coverage: candidate9
has a legal drop at only1/120 training roots and1/16 evaluation roots, while
candidate4 has the largest counts,68/120 and11/16. Equal planned root counts
therefore do not imply equal root-level drop opportunity. This describes the
selected pool only and does not predict action selection or learning exposure.

Reproduction: `audit_frozen_root_drop_availability.py` writes
`frozen-root-drop-availability.json`. The source hashes and exact per-candidate
counts are retained there. No search, learner update, training, evaluation,
registration or run directory was created.

An independent serialized-field inventory over the16 hash-pinned candidate
files found exactly this union of explicit top-level keys: `schema_version`,
`board_size`, `piece_types`, `initial_position`, `drop_allowed`,
`promotion_allowed`, `promotion_forced`, `repetition_limit`, `max_ply`,
`stalemate_result` and `metadata`. `metadata` is explicitly non-semantic in
`RuleSet`; omitted fields use schema defaults, including empty
`semantic_actions`, `declarations`, `automatic_adjudications`, consecutive-
action/alternate-setup/repeated-cycle policies, `pass_enabled=false` and
`no_progress_draw=null`. The defaults describe what candidate files do not
configure; they do not claim that the frozen roots exercised every default
engine behavior. Rule-file capability and selected-root legality remain
separate from descendant search exposure.

The rules are not movement-identical controls: the preceding exact finite-
board movement/path audit found79 distinct behaviors across the96 piece-type
instances in this16-rule batch on 8x8 boards, including78 non-anchor behaviors. Its saved
corpus comparison and setup-symmetry limits remain: it is not a sample of the
Generic rule population, and it does not establish reachability, search
exposure, or learning. See `results/dev_aux/task2633/FINITE-BOARD-MOVEMENT-AUDIT.md`.
