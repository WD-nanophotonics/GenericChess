# Local capture signal does not pass frozen inventory transfer

`LOCAL_SERVICE_VALIDATION_PROTOCOL.md` fixes the distinct service target, use,
new seeds, raw formula, independent data, costs and double-baseline gate BEFORE
coefficients. `LOCAL_SERVICE_LABEL_IMPLEMENTATION.md` binds corpus bytes and
phase order. No old exposed root was reused as independent data. No old global
deployment label, human value or Xiangqi holdout was read.

Generation completed eight reference roots and all twelve real ongoing capture
strata with 28 materializations/0.360 s including joint preprocessing. Corpus
SHA256 9a884ed33633c070b4e5d045bf48617c8d5a34c82384b8354ff62d7c72224cc4.
All eight references were labelled first; raw actor-type means and constant H
were serialized before any NEW deployment label, reference SHA256
66bb31646b53a7b14c722de38b99a843ab26785addba29f65ce5ba9ccdbffcef.
Both games had nonzero reference signal, so all twelve independent children
were then completely labelled. Total: 20 roots, 15,465 materializations,
5.078 s including compilation/replays, below the frozen 60k/30-second gate.
Shogi deployment includes 3,462 opponent drop replies; checks, promotion,
actual history/aux/hand state and terminal vetoes remain active.

Reference successful-actor counts: Chess 5/8/7/7, Shogi 5/10/5/2.
Raw vectors are recorded without Pawn normalization or fitting:

| Game | Raw own-actor service means | H |
| --- | --- | ---: |
| Chess | P=7/32, N=5/8, B=5/8, R=7/8, Q=3/4 | 27/4 |
| Shogi | P=1/6, L=3/8, N=0, S=1/4, G=5/8, B=3/4, R=3/4 | 11/2 |

Deployment Y in sorted victim-type order: Chess B/N/P/Q/R gives 0/0/5/4/3;
Shogi B/G/L/N/P/R/S gives 6/10/9/6/6/4/4. Risks are exact equal-stratum mean
squared successful-actor count error:

| Game | Candidate sum N_t v_t | Zero | Reference constant | Gate |
| --- | ---: | ---: | ---: | --- |
| Chess | 91793/5120 (~17.93) | 10 | 1853/80 (~23.16) | Fail vs zero |
| Shogi | 13151/2016 (~6.52) | 321/7 (~45.86) | 151/28 (~5.39) | Fail vs constant |

Both baselines have positive risks and neither game's candidate improves BOTH
by the frozen 10% margin. The combined finite use is rejected. No vector tuning,
threshold change, extra seed, larger sample or installed evaluator followed.
Nonzero service capability alone is insufficient for an inventory-only static
transfer predictor, let alone global material/WDL usefulness.

Since each real capture removes one ordinary own type t, h=H-v_t. The exact
constant-risk improvement is the mean of
2(H-Y_t)v_t - v_t^2 over victim strata. Tests verify this identity and all frozen
predictions: the inventory decrement cannot correct every context shift. In
Shogi many Y_t exceed H, so a further nonnegative decrement moves predictions
in the wrong direction on those strata; this is a descriptive finite diagnosis,
not a fitted correction or a population-causality claim. Chess's initial constant
likewise does not match the observed post-capture count distribution.

Tests reproduce complete corpus/state/capture choices, independently check
helper against exposed complete attribution evidence and public held-opponent
replies, and reproduce reference bytes/phase order/full validation. The helper
tracks physical tokens only in the declared ordinary Chess/Shogi board/drop
scope; it rejects own promoted prior types, additional board effects or own
hand drift. It does not price held actors or provide generic multi-effect IDs.

Evidence: `data/local_service_corpus_20261004.json`,
`data/local_service_reference_20261004.json`,
`data/local_service_validation_20261004.json`. Existing global-task failures and
unread OLD deployment labels remain intact. Positive diagnostic action counts
and this independently failed prediction test are compatible observations.
Next research needs an independently motivated link between state-dependent
service and an intended static material use; do not turn this into endless
service-count batches or add fitted context terms to rescue the failed gate.
