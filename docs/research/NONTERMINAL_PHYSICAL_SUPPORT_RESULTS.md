# Positive physical support without a terminal-win exception

Base sandbox: 432e6236bacaedcdbbb83cb28234b45b48cf9c7c. The separately frozen
NONTERMINAL_PHYSICAL_SUPPORT_PROTOCOL.md specifies exactly one Bishop/Rook
swap in each earlier full-inventory mate frame. No new random draws or changed
measure, task, source, inventory, Pawn square, hand or common screening family.
Both swapped frames pass the unchanged common quiet screen.

| Game | Capture | Every legal reply | States after capture/reply | Net custody |
| --- | --- | --- | --- | ---: |
| Chess | R(3,3)->(0,3) | K(0,7)->(1,7) | ongoing/ongoing | +1 |
| Shogi | R(3,3)->(0,3) | K(0,8)->(1,8) | ongoing/ongoing | +2 |

The replacement Rook no longer controls the diagonal escape square, so the
capture checks without mating. Raw-position public legal-action enumeration
finds exactly one opponent reply in each case; its public transition confirms
ongoing status and positive ordinary-token gain. Every focal action and reply
was enumerated under the unchanged global task; both R root scores are one.
465 materializations include four additional public replays, about 0.312 s,
within the 4,000/10-second cap. Evidence and protocol/program/frame-source hashes
are in data/nonterminal_physical_support_20261003.json.

The first implementation attempt used internal SemanticAction objects with
public apply_action and was rejected by the API. It produced no complete file.
The runner was corrected to use the existing lossless public-action adapter;
no state, scope, prediction or scoring rule was altered to rescue a result.
Neither Core nor the communication workflow was changed.

As before, these admitted finite placements have positive conditional mass.
They strengthen the support statement: the task can succeed on nonterminal
capture-and-reply branches, without relying on terminal-win scoring. They still
use checking captures that constrain the reply. This is not representative
frequency, quiet-capture support, relative type values or additive material
validation. Do not mix constructed and random frames, install scores, or keep
generating R examples as a substitute for the remaining modelling question.

Next address useful strategic signal and the static approximation contract.
The existence premise is now settled for R in both games, including nonterminal
branches. Any next scoring experiment needs a specified scientific decision
and an independently justified population/use criterion, not a larger budget.
Daily dot discussion may help choose that premise; independent work stays open.
