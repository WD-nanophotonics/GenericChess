# Complete state transport: closure decision — 2026-10-28

Unconditional direct-cast fusion is **NO_GO**. A frozen `Position`/`Piece`
instance does not certify its fields: `Position.__post_init__` checks optional
shape, not owner/type/count validity. New real consumer data are available in
[the PVS result](LEAPER_NEW_FAMILY_PVS_RESULT_20261028.md); their counts do not
supply an exclusive-time estimate or positive saving guarantee.

The existing C builder completes board owner/mapping/integer/truth conversions,
then hands and aux/side/ply, before the packer checks scalar/shape and C ranges.
Moving pack rejection inside the producer loop can change which invalid field
raises first. User-defined equality/integer/truth/mapping callbacks also matter;
exact container class is insufficient as a fast-path certificate. Existing
`test_native_core_payload.py` explicitly preserves mapping exception causes,
large integer transport and older-binary fallback. A candidate must retain that
route for unsupported inputs or prove a narrower admitted input closure.

Hands construction assigns each supplied type, so repeated entries use the
last value; summing or early narrowing is different. Negative hand errors happen
in the builder, upper bounds in the packer. A narrow pure-Leaper candidate may
certify empty hands/aux but must not redefine shared compatibility behavior.

Preserve ordinary C-owned capsule allocation and semantic pack validation,
fresh canonical SHA, initial actor255/history exactness, absolute ply and
provider cancellation/exception behavior. Check/availability use ply0 with
one-use handoff; actual legal frontier imports its real ply. Do not expand that
handoff or remove validation/digest as an alleged transport saving. Existing
compiled targets, hash/undo and availability reuse are baseline.

A conditional candidate is worth one bounded feasibility decision, with staged
errors or explicitly certified exact inputs and unchanged fallback. It is not
permission to rewrite the entire search kernel, change defaults or restart old
negative experiments. Before build/query, freeze the complete prospective
implementation/semantic/cost study and its own truthful total forecast including
unfinished preparation. Completed historical tasks do not count toward the120
minute assessment threshold. If no supported narrow interface or useful total
saving can be established, close NO_GO and select another pure-Leaper question.

Source-only closure assessment: no new Player, solver, game or binary build.
This distinguishes new static inference from independent execution and from
Dot's earlier source-only suggestion. It is a continuation checkpoint.
