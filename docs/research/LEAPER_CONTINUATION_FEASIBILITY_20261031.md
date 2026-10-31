# Continuation allocation: numerical and TT scope —2026-10-31

A zero comparison margin does not make cross-depth value tests independent of
the evaluator. This finite source/arithmetic check rules out that invariance
claim, not singular extensions or value-informed allocation in general. No Core,
Player, solver, game or product modification was performed for this check.

For an all-static uniform-depth negamax tree, changing every static evaluation
from E to E+b changes the root value by (-1)^d b. Max/min preserve a common
additive shift at each layer. Same-depth action ranks remain unchanged, while
comparisons between opposite-depth parities can change.

Concrete consistent tree: root has A,B,C. Their depth-two child leaves are
A=[4,7], B=[10,12], C=[2,3], giving root values4,10,2. For a reduced depth-one
search excluding B, the static evaluations of child A,C are -9,-3, giving
alternative value9. At b=0 the reduced alternative9 is below TT value10; at
b=-1 it is10 versus9, reversing the zero-margin trigger. Both searches retain
their original within-depth action rankings. The standalone calculation checks
all seven integer offsets -3 through3 and is saved with this report. These are
abstract tree evaluations, not claimed realizable Leaper positions or WDL.
Adding a tempo-like offset is a different evaluator; invariance to it is not a
necessary correctness requirement for every heuristic. The result prevents an
unsupported portability claim rather than requiring universal bias immunity.

Same nominal depth/parity alone is also insufficient when some exits are fixed
terminals or declarations and others are static leaves. Quiescence can change
frontier parity and the current Player uses a first-iteration ordinary-Q reserve.
A fixed terminal0 versus heuristic1-b changes preference as b crosses1. This is
an assumption warning, not a demonstrated current search failure.

## Actual source boundary

Pinned [Stockfish search.cpp](https://github.com/official-stockfish/Stockfish/blob/ff7cee4244ec96ea488c402669e3674c0574dce6/src/search.cpp#L1265)
checks a TT-value margin with a reduced excluded-move search. It explicitly
avoids recursive excluded search, suppresses certain TT cutoffs and final TT
writes during exclusion, and uses chess-specific margins/reductions. Selected
sections834–917,1265–1333,1648–1673 were read; no build, benchmark or whole-repo
validation is claimed.

GenericChess source at c08be880a783678ce1d1f865e62f6621d4eaf89e,
search.py361–526/578–696/1099–1138, returns qualifying TT values before expansion,
uses normal TT store after its move loop, and runs runtime children through the
existing push/unwind context. Simply filtering one legal action while retaining
the same unrestricted root TT cutoff/store could return/store information about
a different action set. A hypothetical excluded query must isolate those paths,
preserve full history and extension/Q policy, prohibit recursive exclusion, and
charge all child work/cancellation to the original budget. This is a source
requirement for a future query; no defect was introduced or fixed here.
Ordinary descendants are not automatically invalid TT consumers: reuse depends
on their actual action set and unchanged policy. A new identity/cache framework
is neither needed nor authorized by this observation.

A cheaper candidate source contract is same-depth completed child bounds:
selected lower bound greater than every alternative upper bound. Fail-low PVS
scores are upper bounds, not exact alternative values; aspiration failure and
interrupted iteration cannot be promoted to complete uniform-depth results.
Such separation describes that finite evaluator/search policy, not game-theoretic
quality or a promise that extending its winner helps. The current report does
not implement or benchmark this candidate. Next choose one actual continuation
mechanism only after specifying an informative independently checkable action
endpoint; do not refill prior failed panels or create another chooser.

[Arithmetic source](data/leaper_continuation_feasibility_20261031/arithmetic.py)
and [finite output](data/leaper_continuation_feasibility_20261031/arithmetic-result.json)
are ordinary self-contained data/calculation, not archived prototype execution.
