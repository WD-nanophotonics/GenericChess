# Full actual-inventory Q integration passed

Frozen `JOINT_ACTUAL_FRAME_PROTOCOL.md`, executable
`scripts/audit_joint_actual_frame.py` and
`data/joint_actual_frame_20261004.json` preserve the integration result.
The sampler reuses one exact joint coefficient space, then injects the remaining
14 actual initial tokens uniformly into 55 free cells. Identical-token labelled
multiplicity is constant; all full physical configurations therefore remain
uniform under the old structural law conditioned on dead-free L/N. Applying
the unchanged anchor/terminal predicates gives the same accepted Q law.

At seed 202610040402, the first proposal was rejected for actual anchor check;
the second was quiet and ongoing. Full compilation, preprocessing, both draws
and state checks took 0.172 s. The saved evidence includes all 40 physical
tokens, owner turn, empty hands, aux/history and terminal state. No dead-placement
reject occurred; that outcome would fail the implementation instead of retrying.
The initializer checks exact compiled initial inventory, four L/N and both Pawn
mobility masks, and everywhere-mobile scope of all remaining types.

Tests reproduce the full state/counters and deterministic repeated draws,
verify exact inventory and each token's non-dead placement, and reject altered
inventory or unrestricted mobility. Existing independent exhaustive unranking
tests establish the uniformity of the restricted component. Deadline and proposal
cap failures remain explicit. A test fixture initially assumed mobility masks
were mappings; the compiled representation is a tuple, and the fixture was
corrected to enumerate owners. No sampler/protocol change followed the result.

This is one root's construction/cost gate, not new reference/deployment data,
coefficients, capture coverage or predictive validation. The incomplete old
corpus remains intact. Next freeze a new finite corpus protocol using this
algorithm, with all preprocessing included, unchanged validation semantics and
complete victim-type coverage. Do not increase the failed generator's budget.
