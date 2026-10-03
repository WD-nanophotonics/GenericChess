# Frozen corpus generation stops at an incomplete Shogi stratum

CAPABILITY_CORPUS_PROTOCOL.md was hashed before generation on base
52571007d06d58a2e7b9ef532ab720b5037c7d4d. It fixes four independent reference
roots per game, one fresh legal post-capture child per ordinary victim type,
separate seeds, weights and generation/label cost gates. The numerical-vector
and deployment-risk phases have NOT run. This is a preserved failed generation
gate, not a new all-zero candidate or a partial validation pass.

Both four-root references were generated: Chess used 24 raw proposals
(20 anchor-check rejections), Shogi 76 (67 dead non-Pawn and 5 anchor-check
rejections). These are fixed-seed proposal observations, not acceptance-rate
estimates. No reference task labels were inspected or computed.

| Game | Victim stratum | Raw proposals | Result |
| --- | --- | ---: | --- |
| Chess | B / N / P / Q / R | 1 / 3 / 2 / 4 / 2 | All five complete |
| Shogi | B / G / L / N / P | 8 / 18 / 2 / 10 / 11 | Five complete |
| Shogi | R | 128 | Incomplete at frozen ceiling |
| Shogi | S | — | Not attempted after failure |

In the failed R stratum, 109 proposals have dead non-Pawn placements and 17
have an actual anchor checked. Only two reach the type-capture predicate;
neither offers an ongoing R-victim capture. This does not prove an empty
R-victim population: POST_CAPTURE_SCOPE_RESULTS.md already records an admitted
actual board with such a legal ongoing capture. The current generation failed
to find it within its independent fixed seed/proposal gate.

Generation consumed 35 capture materializations / 0.265 seconds within its
5,000/25-second limit. The decisive limit is proposal/stratum coverage, not
elapsed compute. All eight reference states, ten successful deployment
parent/action/child states, failed-stratum accounting, seed and protocol/program
hashes are saved in data/capability_corpus_20261004.json with complete=false.
There is no missing-type score0, reference/deployment-parent reuse, artificial
removal, type replacement, extra attempt or renormalized Shogi corpus.

Five focused tests reproduce the full partial evidence, verify accounting and
reference separation, independently enumerate every selected parent's complete
public capture choices and replay the selected actual child/history/inventory,
confirm absence of task scores/vector fields, and reject stricter-limit failures
or attempts to increase proposal ceilings. The generator handles terminal and
capture eligibility only; it does not call the task-label routine.

## Decision and next independently justified step

Reject this frozen combined run as an input to numerical inference/validation.
Do not continue to coefficients on the complete Chess component while calling
it the declared combined pilot, drop R/S, insert old scope witnesses or retry
more proposals/new seeds. The fixed references themselves are not quality
evidence and their rare-signal adequacy remains untested.

The concrete bottleneck is prior structural/quiet conditioning. A candidate
efficiency argument is to sample the globally dead-non-Pawn-conditioned joint
physical law exactly BEFORE quiet/capture rejection, preserving Q's target law.
It requires a joint construction, not a retained Pawn-background redraw. If P
is a Pawn layout, W(P) counts valid constrained L/N completions. Its marginal
under dead-free conditioning is proportional to W(P), which may vary across P;
uniform Pawn draws followed by conditional non-Pawn redraw are biased. This
coupling was already established in PHYSICAL_EXCHANGE_SUPPORT_RESULTS.md.

Next derive and cost-bound a complete W-weighted joint sampling construction
without selecting contexts for task success. A small exact counting/proposal
certificate can justify a different algorithm under the same reference law;
mere fast execution or this rare-event failure does not justify expanding the
unchanged generator. Quiet actual anchors and victim-capture conditioning must
still be applied to whole states. Count all preprocessing/proposal costs, not
only accepted draws. No new sampler is adopted yet. Material validity,
held/promoted scope and sealed Xiangqi holdout remain unchanged and open.
