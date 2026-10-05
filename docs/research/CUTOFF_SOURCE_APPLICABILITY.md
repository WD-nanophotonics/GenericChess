# Imported cutoff-source applicability before the new root observation

2026-10-05. Source/compiled metadata audit only; no new game outcomes here.
The declared single structure is an IMPORT at absolute ply998, not a complete
998-move reconstruction or an opening-reachable sample. Source is PublicGame's
execution objective, not a second independently implemented rules oracle.

Compiled Western support has max_ply1000, repetition_limit100000,
repetition_policy draw and stalemate draw. Automatic/consecutive adjudications
are empty, no-progress draw absent; IR declarations and repeated-cycle target
conditions empty. Current native board guards use only current pieces, source
base/promotion, rights/EP and occupancy; the pinned Western definition contains
no additional history-dependent actions. Semantic terminal checks complete
legal availability/checkmate/stalemate before repetition and the ply limit.

For ANY consistent hypothetical prefix with998 plies, no position occurrence
can exceed999 at this root or1001 after two more actions. This is strictly below
100000, regardless of omitted prefix identities. No enabled adjudication needs
the missing prefix. Rights0/EPNone/current board and absolute ply therefore
determine the next two actions and objective; later generated histories are
retained normally. Condensed count1 is a representative for this local horizon
equivalence, not a claim of full valid history or arbitrary imported-counter
equivalence. An inconsistent count>=100000 is outside this premise.

PublicGame rechecks its cached root terminal result freshly. If compiled
metadata/fingerprint drifts or any premise fails, no cutoff label is qualified.
This lemma does not extend to FIDE repetition/no-progress or Shogi/Xiangqi
adjudication. It does not make compressed history acceptable to the old external
DTM bridge. The new label's scope is explicitly this synthetic goal boundary.

Cost feasibility is a separate observation: complete root children/selected
opponent reply sets still have to fit unchanged128/5000/15s caps. A source
definition alone does not prove informative disagreements or positive margins.
