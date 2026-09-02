# H50B1-R4 Native differential blocker

Status: `F50B1_R4_CERTIFICATION_BLOCKER`

Checkpoint under audit: `H50B1-R4_F50_SEMANTIC_NATIVE_PROMOTION_IDENTITY_CLOSURE`

Parent authority: `34a5fd67d121d9912fad6292e99784bf62e9bf88`

## Blocking finding

After the authorized Native promoted-piece correction, the frozen R3
Native/Python differential reached the declaration path and found a second
semantic mismatch.  On the same Standard Shogi declaration state at
`score=23`, Python Core and Native both classify `claim_owner_0` as `LOSS`,
but their weighted scores differ:

```text
Python: actor=0 outcome=LOSS weighted_score=23
Native: actor=0 outcome=LOSS weighted_score=1
```

The mismatch was raised by the actual declaration differential in
`scripts/audit_h50b1_r3_native_differential.py`, not by a citation-only
fixture.  It occurs after Native position packing and direct calls to
`semantic_assess_declaration`; the Python side calls Core's public
`assess_declaration` on the same packed-state construction.

## Reproduction

From the R4 worktree, with the fresh Native build loaded:

```text
generic-chess-flow.cmd heavy -- .venv\\Scripts\\python.exe scripts/audit_h50b1_r3_native_differential.py
```

The first failing assertion is:

```text
AssertionError: declaration mismatch at score=23:
{'declaration_id': 'claim_owner_0',
 'python': [0, 'LOSS', 23],
 'native': [0, 'LOSS', 1]}
```

## R4 changes already completed before the blocker

- Native `inherit_compiled_masks` promotion generation now returns only
  `promotion=255` for an already-promoted actor.
- Native packed-action validation now rejects forged re-promotion actions.
- The R3 audit repacker obtains packed base type from the authoritative
  pre-action board while retaining public actor/current identity.
- Promoted-piece and legitimate-promotion focused tests pass.
- Fresh Native payload version remains `4`; no payload-version change was
  introduced.

Fresh Native binary observed before this blocker:

```text
sha256=aa735071b4dadbfb22e64467d10b4ab27ad4880f4933757a0f55bbd1d77644f9
size_bytes=354816
```

## Scope and disposition

- The R4 production correction is the only production change in this
  checkpoint; no further production patch is made after the differential
  failure.
- The weighted-declaration mismatch is now the first preserved R4 witness.
- The remaining R3 certification requirements are not claimed complete:
  full 24/21 matrices, complete history/automatic witnesses, isolated H50A
  regression, state-size measurements, and cumulative provenance remain
  pending behind declaration parity.
- A subsequent corrective order must reconcile Native's weighted declaration
  computation with Python Core and add a direct regression for the exact
  `score=23` state before certification resumes.
