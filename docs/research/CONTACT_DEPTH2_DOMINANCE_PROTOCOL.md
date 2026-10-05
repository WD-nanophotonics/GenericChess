# Fixed depth2 static-leaf operator, saved-tree dominance continuation

Freeze terminal-first minimax of root own action then enemy action, cutoff at
ply2, common31 denominator/owner-zero score. ONE coefficient vector across
all leaves; two declared contact boxes separately, unit/zero separately.
No check extension, quiescence, stand-pat action or goal-calibration claim.

Negative interposition: each of four promotion branches has actual terminal
reply-1, exact score floor, so min is-1 without completing188 full-width edges.
Kxd7 has all35 reply states saved, none enemy-winning terminal. Their native
ordinary counts are qualified; min score strictly>-1 for all supported vectors.
Thus ALL three fixed-depth2 methods choose Kxd7. Read existing states only.

Positive pinned-Queen: all21 root-child scores are saved/frozen. Every enemy
move is King/Q/N ordinary movement/capture, no hand or promotion; a nonterminal
reply can only preserve or decrease root inventory score. Terminal reply value
is-1 or0, never+1 on this Western enemy turn. Hence any branch min<=max(0,
its root-child score). The contact-selected Q promotion has a COMPLETE singleton
King reply with inventory unchanged and positive score; old certified strict
root-child margins imply it STILL dominates every other branch under depth2.
This is a global-coefficient argument, not independent leaf endpoint choice.

For unit, R h8xg8 has maximum root-child unit score; verify NEW full enemy reply
set and its sole King reply preserves score. Earlier canonical Kxe5 has a
saved Qxh8 reply lowering unit score, so cannot tie it. Other earlier root
actions have lower root unit score; full score/tie table remains unchanged.
For zero, verify ALL enemy replies to its earliest canonical Kf6: reuse saved
Qxh8 successor, materialize only previously unobserved others. If no reply
is enemy checkmate then branch min0, the global zero-score maximum; otherwise
leave selection unproved. Do not replace root or canonical tie.

Continue same pinned-Queen128 event/5000 explicit action/15sec cap: old34 events/
622 entries/0.219sec plus NEW edges/entries only. Save complete action lists
before processing. Terminal freshness/full history/rights/EP preserved. No
source/human/goal labels beyond actual new enemy successors. Report this as
EXPOSED search-operator development, not new held-out strength evidence.
