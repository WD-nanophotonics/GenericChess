# F61 Standard-Shogi calibrated seed-59011 R27B — Heavy declined

R27B proposed only enlarging the execution wall bounds for the fixed
three-pair seed-59011 replication after R27's first capped game hit its
3,600-second bound. The candidate, node budget, ply cap, openings, and
decision rule were unchanged; the proposed bounds were 7,200 seconds per game
and 43,200 seconds per stage.

- published sandbox: `448df426b0aacf4b0abb36d7eb55bd2f1a6f6739`
- Chat request: `GENERICCHESS-20260914-033949-c041fc92`
- Chat plan approval: `APPROVE`
- plan SHA256: `15e2e3f68b9a1a5d2462d361c07254f1ee2ddc58e75e3277c10755283dc01f69`
- resource envelope SHA256: `8f8fd41656a06a3364c300d9edf0269d05709e7b9b8a8778c0bea1a84824f209`

The registered Supervisor declined the Heavy request. The prior capped run
already showed that one fresh game can exceed an hour; permitting two hours
per game and a twelve-hour stage is disproportionate for refining an already
neutral optimizer-seed candidate and conflicts with the cheap,
decision-sufficient strength-witness requirement.

No R27B Heavy was launched, no additional games were run, and no replication
decision is claimed. Seed-59011 remains inconclusive on the existing R15
evidence. The Courier loop should now request a cheaper actual-strength
discriminator or a new learning/generalization mechanism.
