# Guarded graph proof scope

This prototype proves finite rule wins under a checked history quotient. It is
not a complete replacement for the full GameSession tree solver. No existing
player or proof bank uses it. `CANDIDATE_WIN_GRAPH` needs independent verification.

The guard admits only the baseline executor with Position-only legality and
board terminal conditions. It rejects declarations, semantic executors,
continuous-check loss, no-progress rules, automatic adjudication, consecutive
and repeated-cycle conditions. Ordinary draw repetition and the ply limit are
handled explicitly. Supported baseline drops, promotion and hands retain their
full typed fields. A failed guard is UNKNOWN, never a draw label.

The verifier reconstructs positions from the actual root through public action
execution. It never trusts producer sessions, position labels or omitted
frontiers. Every target node has one legal edge, every defender node all legal
edges. All edge ranks strictly decrease to an actual winner terminal. These
conditions inductively supply a finite winning strategy.

A DAG merge requires exactly the same full typed Position, including owner,
base/current type, promotion, hands, auxiliary fields, shape and rule ID.
Repetition identity must additionally be injective across reachable graph nodes.
Strict ranks then prevent any path from visiting an identity twice. Each future
identity must have at least one safe occurrence remaining in the actual root
history; the current root cannot recur. Root rank must fit remaining plies.
Together these conditions prevent a canonical position proof from silently
crossing a real repetition or horizon draw. Root record/state/result admission
must preserve the actual ongoing GameSession; a resigned or otherwise ended
session cannot be restarted by the canonical constructor.

Canonical sessions are a scoped construction already used in the audited
endgame graph: compile the fixed valid rules, replace the immutable compiled
initial Position, and execute public rules. This represents legal in-check
contexts rejected by the separate RuleSet initial-layout validator. Base rule
fingerprint alone does not identify the context; the explicit full root and
record are mandatory. This is not a claim that every context serializes as an
accepted RuleSet initial JSON.

Work units differ: PN visits tree nodes; graph search stores positions and
expands frontiers, and graph verification visits shared positions. Construction,
verification and actual cursor costs must all be reported. Sharing representation
does not establish efficient search; the BFS prototype may spend its budget on
an unhelpful frontier. Stored-table proposals test representation separately and
retain the table's prepaid construction cost. Neither table nor positional WDL
provides a learning reward.
