# Frozen resource-mode root feasibility

2026-10-04; baseline306403d66e8f7ba0c1e1821d42739de447dddb55. Freeze before
numerical admission/choice observations. Implements RESOURCE_MODE_CONTEXT_DESIGN,
not a prior or empirical kernel. No score, human label, future capture reward,
goal observer or actual state transition is requested by this pilot.

Exactly six strata, ordered Chess then Shogi, within each game as listed:
Chess board/P/P seed20261004101, board/P/Q seed20261004102, board/Q/Q seed20261004103;
Shogi board/P/P seed20261004104, board/P/TP seed20261004105, hand/P seed20261004106.
Allocation42,42,44 WHOLE proposals per game's three strata; at most128/game.
Independent PRNG per stratum. Stop proposals at FIRST structural, unchecked,
ongoing admitted root, or exhaust its fixed allocation. No transfer of unused
allocation, retries, mode substitution or selection for useful action outcomes.

Use the labelled full-initial-resource construction described in the design.
Original own base mark uniformly drawn; only mark promotion/hand differs.
Shogi file and rank draws are independent per owner; a same-square Pawn collision
rejects the entire proposal. No within-proposal collision repair. Other board
tokens sampled uniformly without replacement from remaining squares.
All board modes must have nonempty empty-board mobility, Pawn rank/nifu rules
hold, anchors have initial counts, Chess per-owner and Shogi global base-resource
conservation hold. Both anchors unchecked; fresh terminal probe is ongoing.
Chess rights/en-passant empty. Synthetic ply0/single history record is explicit;
no initial reachability claim. Full resources include any hand-marked token.

After admission, exhaust PublicGame actions including available declarations.
Canonical action IDs include all semantic/promotion/drop fields. Unique IDs;
128 choices/root maximum. Encountering choice129 marks that root enumeration
INCOMPLETE and does NOT trigger another proposal or discard/change the root.
Other fixed strata may still be assessed within the common budget. At most5000
enumerated choices across the pilot;15seconds including compilation and roots.
Clock checkpoints throughout semantic enumeration/probing; cooperative time cap
is not OS preemption. Timeout retains already recorded evidence and declares
unfinished strata incomplete; no resumption/retry with another seed or budget.
ZERO public child transitions and ZERO coefficient/goal observations.

Save every rejected-proposal reason/count, admission attempt, root board/hands,
origin-refined tag, synthetic history/auxiliary state, all visited canonical IDs,
enumeration completeness and source hashes. Do not turn a partial list into
an action distribution. The bounded first-admission count is not an acceptance
rate estimate. A failure establishes only bounded feasibility missing, not an
empty context law or zero material value.

Decision: if all six roots admit and complete choices fit caps, root construction
is feasible on these six observations. This licenses separately designing a
four-ply H2 path law, not sampling coefficients, inferring positive rewards,
declaring mode completeness or increasing caps. If any stratum fails, retain
the failure and investigate its observed cause under a changed premise before
any new empirical experiment. Actual-child closure, anonymous drop traces and
independent deployment labels remain distinct unqualified gates.
