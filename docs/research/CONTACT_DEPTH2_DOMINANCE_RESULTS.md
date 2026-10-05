# Fixed depth2: shared-coefficient dominance, not new strength validation

The frozen operator is terminal-first root max/enemy min, cutoff after two
actual plies, material/31 on ongoing leaves. Each contact law uses ONE vector
throughout the tree. No quiescence, check extension or legal stand-pat action.
Protocol: CONTACT_DEPTH2_DOMINANCE_PROTOCOL.md; saved report:
data/contact_depth2_dominance_20261005.json.

Negative interposition: every promotion has an actual enemy mate reply and
therefore minimum score-1. All35 saved Kxd7 replies are nonlosing terminals or
qualified material strictly above-1. Contact, unit and zero consequently all
choose Kxd7. This is an exact choice certificate for the fixed depth2 operator,
without paying the188-edge full-width cost or recalibrating static scores as WDL.
It repairs this exposed depth1 tactical failure, not all tactical failures.

Positive pinned Queen: the contact-selected Q promotion has one enemy reply,
preserving its strictly positive material score. Enemy ordinary King/Q/N moves
can only preserve/decrease root inventory, and enemy-turn terminals cannot
give root value+1. Thus every competing branch is bounded by max(0, its child
score). The frozen strict child margins certify the contact choice under both
global coefficient boxes, without switching coefficients between leaves.

Unit instead chooses R h8xg8: its complete singleton reply preserves2/31;
the earlier tied Kxe5 has a saved Qxh8 reply worth1/31. Zero's earliest Kf6
has all14 replies verified nonlosing at this cutoff, so retains score0/tie.
These are exact fixed-depth score choices, not exact eventual game values.
The new unit R choice is outside the installed KBK/KRK source domains; the
old unit Kxe5 mate-window counterexample does NOT transfer to that new choice.
Contact's already saved winning branch/value1 remains applicable. Zero's
saved window counterexample remains applicable, but its eventual value is unknown.
No strict full-WDL or tie-invariant contact gain is established.

Only14 NEW public transitions and184 explicit entries were applied:1 R branch
reply and13 previously unobserved Kf6 replies; the old Qxh8 successor is reused.
Pinned-Queen totals are48 events/806 entries/0.328sec, within unchanged
128/5000/15sec caps. Negative saved evidence is read only, not replayed.
All new states preserve full history, terminal freshness, rights/EP and native
identity scope. No source queries, human labels, holdout reads or tuning.

Interpretation: operator depth changes what usefulness comparison is meaningful.
These exposed mechanisms are development controls; next freeze an independent
root/source opportunity and separate cutoff evaluation from expansion-order use.
