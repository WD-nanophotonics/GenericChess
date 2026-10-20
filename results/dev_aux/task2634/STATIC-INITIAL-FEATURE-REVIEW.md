# task2634 static initial feature review

## Question and frozen scope

Does the raw-novel movement batch from task2633 present distinct initial inputs
to the unchanged task2621 fixed-scale Generic adapter? The predeclared read-only
scope compiles the same16 pinned candidate rules, reads the adapter channel names
and initial feature vectors, and performs a separate direct board/hand count
reconstruction. It makes no legal move and reads no outcome or search value.

## Result

All16 candidate rules compile through the unchanged adapter. Each exposes the
same10 channels in the same order: board P as unit, board A/B/C/X, then hand
A/B/C/P/X. Every candidate has the same initial vector, all zeros; direct
owner/type count reconstruction matches every adapter component. This follows
from the balanced mirrored initial material, not from movement equivalence.

Together with task2633, the batch therefore has novel non-anchor movement
behavior in the scanned result-artifact corpus but no initial material-feature
distinction. Movement-rule differences can affect this material-only learner
through subsequent legal trajectories and terminal/search targets; this static
check demonstrates neither feature activation after moves nor learning or
strength.

## Decision and limits

This is an adapter-input contract check only. It does not validate full-history
exposure, root-pool suitability, playout outcomes, search, training, evaluation,
or transfer to built-in Chess/Western rules. Keep these16 starts out of any
future validation pool; they are now exposed by this static inspection and the
task2633 generation run. A future legal feature-activation probe must be a
separately bounded, outcome-blind registration, with all actions and UNKNOWN
states preserved and no strength claim.

Plan SHA-256:
`945f266ce656dcd25be62eacb1bf060d474ba64f2eeaad88195ab4942087b1ff`.
The result is `static-initial-features.json` (SHA-256
`66c26723444944b2f65ea7ea13a2a303ce9baf221ccc9f303f96542f59289902`), bound to
candidate index SHA-256
`1b7d11d7f79040a3641f589a6eaa8ae593cc5ffe0077678f1bc12bc856e05f5e` and the
six source hashes in `plan.json`.
