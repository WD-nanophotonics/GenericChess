# Equal-depth check of frozen candidate96 price-sensitive choices

## Preregistered question and decision consequence

The frozen candidate96 panel found 22/56 static_v2-versus-Unit first-action
differences among paired contexts with identical pre-move state hashes and an
8,192-node cap in each arm. Completed depth was not always equal. The question
is whether those choice differences remain when the same frozen positions are
searched to the same completed depth, so this finite decision-sensitivity
evidence is not explained solely by different completed depths under the node
cap.

If any action differences persist, report finite equal-depth sensitivity for
these saved generated-5x5 contexts. If none persist, retain the narrower
equal-node-budget interpretation and identify depth asymmetry as an unresolved
explanation. Neither outcome estimates utility, causal game benefit, population
transfer, or a universal price; neither changes the current evaluator/default.

## Frozen protocol

- Inputs only: the eight saved `candidate96/rule-522001..522008.json` files,
  corresponding frozen profile files, and paired rows in `games.jsonl`.
- Select exactly the 56 paired contexts whose Unit and static_v2 first
  candidate queries have the same state hash and each recorded exactly 8,192
  nodes. Deduplicate fixed-foe repetitions by root, owner and exact state hash;
  the prior saved-data audit found 37 unique contexts and 14 distinct first
  action changes under the node cap. Fail closed if reconstruction disagrees.
- Reconstruct each complete session prefix from the saved opening and preceding
  recorded reply actions; verify the exact saved `state_before` hash. Do not
  launch games or modify frozen records.
- Compare only the fixed Unit and static_v2 material checkpoints under the
  public `SemanticSearchEngine`: exact D3 completion, no node/time deadline,
  qdepth 0, TT disabled and root-window pruning disabled. Hold ruleset, root,
  history, evaluation/search switches and action serialization fixed. Record
  nodes and elapsed time separately; search work need not be equal at equal
  depth.
- Report the 37 state-clustered action/score contrasts, including prior and
  matched-depth choice status. Preserve all failures/UNKNOWN; no outcome labels
  are used. A reproducible action flip is decision sensitivity only.

Estimated cost is under 10 minutes from prior sub-second 5x5 D3 searches; it is
one bounded run (<120 minutes), requires no Dot assessment, and is cheaper and
more diagnostic than new games, deeper searches or training. No product/default
change is authorized by this diagnostic alone.
