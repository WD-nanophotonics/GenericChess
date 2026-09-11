# GenericChess F82: champion adoption and repeatability plan

Status: `C1_CHAMPION_ADOPTED_REPEATABILITY_PROTOCOL_FROZEN`.

F81 is closed. The confirmed F78 child
`f0ca40ce5aaad97fb6437cb3a8a22d97791f9fe5939f48089becb27dbff82ec4` is now
the model-level champion/parent C1, replacing Gen1 parent
`d0e6a02482bb316e657ec6ef5c4f9379e6e7946d2da1a9a38647175567aecab4`. This
adoption is recorded in
`artifacts/f82_champion_adoption/champion.json`; it does not promote `master`.

No training, teacher search, self-play, Arena, Heavy job, opening generation,
candidate fitting, or production evaluator/search change is authorized by F82.
The next candidate is labeled C2 and must warm-start from C1 under the frozen
protocol below.

## Sealed history

The F78/F79/F80 selection corpus, F81 final-confirmation corpus, F75/F77 triage
corpora, and F62 historical strength evidence are sealed. They may support
regression, identity, or mechanism comparison, but cannot enter C2 training or
candidate selection. F81 corpus ID
`67b9dafc51a618645c3328228c30a8744cc8f988395a7d54d382b65276dc935c` remains
final-evaluation history only.

## Frozen C2 mechanism

C2 remains `PARENT_ANCHORED_FULL_RESIDUAL`. Freeze input mean/scale, target
scale, output bias, width, hand binding, perspective, ruleset/native scale,
and board/hand/dynamic/spatial/control weights. Only `hidden_weights`,
`hidden_bias`, and `output_weights` may update. Output-only pointwise,
output-only pairwise, and parent-replacement redistillation are prohibited.

Pre-register the F78 optimizer family: full-batch Adam, 100 steps, learning
rate `0.001`, proximal coefficient `0.001`, parent anchoring, and the same
registered deterministic backtracking safety sequence. No hyperparameter sweep
or result-driven retry is allowed.

## Authority and stop rules

Offline fit, ranking, agreement, regret, and teacher metrics remain
diagnostic. C2 strength authority is the frozen funnel
`bounded correctness/safety → Arena2 → Arena4 → Arena8 → fresh final
confirmation`, with fresh, mutually disjoint training, selection, and final
corpora. Only one pre-registered C2 candidate is allowed. Failure stops that
candidate; it cannot trigger optimizer or alpha changes followed by a retry on
the same evaluation corpus.

F82 only freezes this protocol. The next order is F83 fresh,
champion-relative, corpus-disjoint evidence acquisition with resource
estimation before any expensive search.
