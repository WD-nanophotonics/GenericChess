# F61 Standard-Shogi R19 trusted-target screen — declined

R19 was not executed. Chat returned an explicit compute-plan `HOLD`, and the
registered Supervisor reviewed the exact plan and signed a scientific ruling
to decline it rather than authorize Heavy.

## Immutable checkpoint and plan

- Sandbox/origin checkpoint: `90353a178e4d5dbf1a6025bedb405c45aea621a1`
- Implementation: `scripts/f61_pointwise_trusted_target_screen.py`
- Chat request: `GENERICCHESS-20260914-001952-faa5a71f`
- Plan SHA256: `eb552e8bd9933776a2e001ecf32a615fa03b8f14a89663d250276d1d742117cb`
- Resource-envelope SHA256: `551a015c2ec461d1ff1d9b240093101313e22c48bda737526c86173dda1c92c3`
- Chat decision: `GENERICCHESS_COMPUTE_PLAN_APPROVAL=HOLD`

The exact command was never launched. No Heavy process, Arena pair, candidate
checkpoint, or playing-strength result exists for R19.

## Supervisor scientific ruling

The proposed run would spend an expected five wall-hours and ten CPU-hours
reconstructing full F59 trust spectra merely to screen one fresh Arena pair.
That cost is disproportionate to its ability to distinguish the remaining
failure layers after neutral R16–R18 play. The trusted-target experiment is
therefore declined as written, without changing the parent, evaluator, search,
or production ruleset.

The next mainline step must be materially cheaper and directly distinguish
learning-objective failure from search/deployment cancellation, using cached
evidence or a sharply bounded witness first. This report does not authorize a
replacement compute request or any promotion.

