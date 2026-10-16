# Generic evaluator transfer: evidence and one cheap next check

2026-10-16. Revisable research notes, not a product/model/policy change.
The two CHAT memoranda are reference suggestions. Current finite search work
continues; no solver, training worker or new architecture was started here.

## Primary literature actually examined

Tomašev et al. trained separate AlphaZero models from scratch for their chess
rule variants. Section2.3 specifies one million training steps/batch4096; their
piece-price fit uses self-play outcomes. This supports rule sensitivity and a
particular empirical price projection, not a same-network transfer result or
intrinsic uniquely identified state-local prices.
[2020 paper, sections2.3/3.8](https://arxiv.org/html/2009.04374v2).

Stockfish's NNUE account describes sparse active-column accumulation, updates
from changed features, and HalfKP's king-dependent features. A king move can
require a full refresh. Quantized accumulation still needs overflow control.
These principles motivate measuring changed-input work and refresh frequency;
they do not supply a correct generic promotion/drop/aux/history update scheme.
[Official NNUE account](https://official-stockfish.github.io/docs/nnue-pytorch-wiki/docs/nnue.html).

Polygames uses convolutional policies and global pooling to remove fixed spatial
size from the architecture. Shape compatibility is useful, but alone is not
learned semantic compatibility.
[Author-hosted Polygames paper](https://www.lamsade.dauphine.fr/~cazenave/papers/Polygames.pdf).

Soemers et al.'s2021 preprint transfers input/output channels using consistent
Ludii representations; its rules-to-channel relation is deliberately coarse,
including piece-name matches and ludeme-tree distances. It reports positive
and negative transfer. Its transfer training used20hours on8GPUs/80CPUcores,
so it does not establish this project's desired5–10minute adaptation target.
A representation-preserving parameter copy and a strategy-preserving transfer
between changed games are distinct claims.
[2021 preprint sections3/4](https://ludii.games/publications/ARXIV2021.pdf).
This preprint is superseded by the2023 TMLR paper. During the initial pass,
OpenReview returned browser verification and the2023 text was not reviewed.
During the next segment its author-hosted PDF became available through the
author publication page. The updated scoped review is below; the earlier access
failure remains historical evidence. The author repository identifies the
implementation split, not a ready GenericChess adapter.
[Author repository](https://github.com/DennisSoemers/Transfer-DNNs-Ludii-Polygames).
Do not silently attribute the2021 experimental details to an inspected2023 text.

## Actual local boundary check

Using the existing generated4board seed34101's original setup, PRIMARY created
three explicit RuleSets: original; replace only X movement by a forward leap;
change only max_ply512to511. Each creates its own actual initial GameSession.
All preserve type axes/setup/promotion/drop. All yield301-dimensional identical
SparsePositionEncoder vectors with supplied dynamic values explicitly zero.
The movement variant has four legal actions, like the original, but two physical
moves differ. The max-ply variant leaves these initial legal actions unchanged;
no late terminal contrast was executed. Core/Native initial terminal status
agrees for all three. The original encoder rejects both other fingerprints.

This is a cross-bound-model representation collision and a working protection,
not a deployed bug, trained prediction failure, or proof of different optimal
values. No history was fabricated by replaying the old route under changed rules.
Results/source: the matched-D2 archive's representation-plan/results/py.
Existing STATE_INPUT_FEASIBILITY.md separately documents base/current identity
and complete-history limitations; its source review is not new execution here.

Consequence: a future generic weight-transfer experiment can use an explicit
mechanical mapping as an approximation. Test it, rather than rejecting every
mapping unless it proves strategic equivalence. Equal dimension and names do not
justify silently bypassing the current binding or claiming zero-shot strength.
Do not repair this by adding an opaque fingerprint/hash input and calling the
result generalized. Incremental inference and cross-rule learning remain separate.

## Proposed smallest later comparison

First select ONE available teacher subdomain with explicit rule/label provenance,
coverage and cost, using existing owner's tools. Preserve EXACT/PROVED-BOUND/
APPROX/UNKNOWN and independent test positions. Full WDL is necessary only for
an exact-WDL claim, not for an explicitly approximate pilot. Use the same labels,
full rule/history semantics and finite search to compare scalar material with
one cheap state-interaction candidate. No broad curriculum/NNUE framework first.

For transfer, choose one source/target rule axis and a declared mapping. Compare
zero-shot, identical-budget fine-tuning and scratch, including source training
cost, target inference/search cost, missing outcomes and old-rule forgetting.
The existing fingerprint guards stay; an experiment binds the mapped copy to the
new compiled rule explicitly. No universal rule-distance ordering is assumed.

For local prices, define a target before fitting. In V=b+n·w, one state value
cannot identify all state-dependent entries of w; any perturbation perpendicular
to n leaves the dot product unchanged, and a free b adds another ambiguity.
A fixed material projection under a declared distribution can still be useful.
Legal counterfactuals/action ranking or constrained projections are alternatives,
not automatically interchangeable labels. Actual common-future games also show
why a finite policy return must not be silently labeled exact optimal WDL.

## Actual action-channel check on the causal drop state

The later P/Xdrop intervention supplies two legal actions to the SAME square.
Actual current V0features differ in actor/drop identity entries; V1's21numeric
base entries are identical, but its actor/drop categorical tuples differ
[2,4,2,2]versus[3,4,3,2]. Native packed actions also differ and roundtrip exactly.
This is two actual API encodings/identity checks, zero trained inference/search.
A from/to-only proposed head would alias them; the EXISTING V1 does not.
Reuse the current typed categories if testing transfer. They are per-RuleSet
indices, not a proof equal index means equal mechanics across changed rules.
No learning-module edit or new policy-head interface was needed. Late source-
copy verification independently binds categories and Native identities; the V0
floating vector remains original execution evidence, not separately recomputed.

A final bounded census actually encodes ALL848legal actions on the eight paid
parents plus the causal drop state using currentV1numericbase+categories.
All nine roots complete;848distinct vectors, zero colliding groups there.
No search/game/training, successor comparisons or new policy interface was
needed. This is original API execution, not included in the earlier source-
only six-consumer receipt pass and not independently replayed. These generated
roots do not cover auxiliary-effect action aliases or all DSL mechanics.


A concrete auxiliary-effect boundary was then actually started and checked:
reuse the existing phase_graph regression, changing only aU's geometry to match
aV. At its legalphase1root both actions have equalV1base/categories[0,7,7,0],
but setphase to(2,0)versus(3,0), producing different complete children. Actual
Core/Native board/hands/aux/side/terminal fields agree for both transitions.
This explicit one-field fixture is not a generated-frequency estimate, a trained
policy failure or an optimal-value proof. It qualifies the848-generated-action
negative census: no universal injectivity claim. Ordering ties remain permitted,
and complete Native action identity/checked search retain both alternatives.
Keep currentmodels/API; a later scoped teacher test can examine consequence
before changing representations. No search/game/training was run for this case.
These late original executions are not included in the635-member source replay.


Late finite consequence closes the prepared auxiliary-alias question in the SAME
active segment, without resetting its clock or changing the4query caps. Existing
Core/normalNative each completeD2frombothchildren (rootactionD3): aV Q=-6,
aU Q=-5, independently matching. The declared static fixture values are
K/W/B/S0=0,S3=3,S5=5,S6=6. This is a source-exposed finiteobjective counterexample:
equalstate/actionV1inputs cannotexpress that strict preference foranyparameters.
It is not trainedfailure, optimalWDL orreason toreplaceapproximateordering;
Native/checkedsearchstillretainsbothfullactions.

These4latequeries and2diagnostictransitions are additional to the sealed
4165query/96game replay, not newgames or retroactively included in that receipt.
Separate normalandpublication-source searchdisabledfullstate/history/PV checks
bothpass; counts agree. Newactualquerytotal4169, physicalgames still96. The
original635ZIP remains unchanged. No learning/solver/API/default change.

## Final2023 paper: updated source access and useful distinctions

The [author-hosted final PDF](https://www.ericpiette.com/papers/tmlr23.pdf)
was inspected in sections3-4 and AppendicesB-E. Channel mapping uses encoded
information, with piece-name/tree-edit heuristics; internal weights are copied.
It reports positive and negative transfer. Transfer training uses20hours on
8GPUs/80CPUcores per source; fine-tuning adds20target hours against a20hour
scratch baseline, treating source pretraining as free. There is one initial seed
per source and300role-balanced evaluation games per pair. These experiments do
not establish equal-total-cost superiority or this project's5-10minute target.
This is a scoped reading, not a claim all39pages/implementation were reproduced.

Our cost decision is therefore explicit: with pretraining cost C0 and target
costs Ct for adaptation and Cs for scratch at the SAME target quality, savings
across k targets require C0+k*Ct<k*Cs. If Cs<=Ct, reuse never recovers C0 through
this saving alone. A pre-existing source model may legitimately have zero
incremental acquisition cost, but that assumption must be named. If zero-shot
already meets the target, adaptation-to-target cost is zero; additional samples
cannot be described as necessary to reach it. Label accuracy and actual search/
play quality remain separate targets. This accounting is our inference, not an
additional experiment in the paper.

The completed PRIMARY study is NATIVE_TEACHER_AND_TRANSFER_20261016.md. It
separates finite-Q horizon, search-order cost, cosmetic channel mapping and actual
rule transfer; no network, solver, learning worker or policy API was added.
