# New corpus gate after independently verified joint sampling

Base c8b7002a1b561ef058dd786a9926ac7fb2972fe9. The old failed corpus remains
unchanged and incomplete. This new algorithm removes independently quantified
intrinsic Shogi rejection, preserving Q exactly; no larger old-generator budget.
Use the unchanged POST_CAPTURE_VALIDATION_CONTRACT.md task, loss and 10% margin.
No human values, Xiangqi holdout or coefficient tuning.

Chess uses the original actual-inventory structural sampler. Shogi uses one
reused ShogiJointSampler: uniform joint Pawn/L/N integer unranking then uniform
remaining-token injection. Apply identical quiet/ongoing checks; dead non-Pawn
output is an implementation failure, never ordinary retry. Include both games'
compilation and joint preprocessing in total cost.

Freeze four equal-mass reference roots/game. Seeds Chess 202610040501 and Shogi
202610040502; at most 128 proposals TOTAL per game's reference, no actor scores
or success-based selection. No reuse of previous numerical fixtures as data.
Freeze one deployment child per compiled initial ordinary victim type, equal
mass 1/5 Chess and 1/7 Shogi. Sorted-type seed bases 202610040601 and
202610040701 respectively, plus zero-based index. At most 128 fresh joint/full
proposals per stratum. Reset accepted parent to owner 1, exhaust real legal
captures of the target type, condition on at least one ongoing successor, then
uniformly select among unique capture actions. Preserve actual child state,
history/aux/check/opponent hands and own initial counts minus one victim.

Require all eight references and all twelve deployment strata. Reference and
deployment-parent overlap fails the run, never adaptive replacement. Save all
states/seeds/reason counters and program/dependency/protocol hashes. No Y or v
during generation; missing strata cannot be scored zero or renormalized.
One process, at most 5,000 capture materializations and 25 seconds including
compilation/preprocessing. Proposal exhaustion saves partial evidence; deadline
or transition abort cannot qualify. No new seeds or increased gates after failure.

After corpus bytes are frozen, a separate label runner may enumerate complete
own board actors/replies on the eight reference roots, freeze
v_t=(sum_reference S_t)/(4*n_t) and reference-only constant, then label twelve
deployment children. Preserve all replies including drops/check evasions;
fail on no-contest/empty nonterminal reply/incomplete enumeration. No early
deployment labels, fitting, truncation or partial zero scores. Gate: at most
20 roots, 60,000 materializations, 30 seconds total, one process. Nonzero
reference signal and positive baseline risks required per game; evaluate
R(h)<=0.9 R(0) AND R(h)<=0.9 R(constant). All-zero reference stops that game's
coefficient-use qualification, not evidence of zero true mean. Report finite
scope only, no material/WDL/strategic-use claim or own-hand/promoted extension.
