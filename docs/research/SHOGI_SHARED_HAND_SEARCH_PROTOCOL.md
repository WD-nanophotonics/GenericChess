# Shared hand-box arithmetic plus one new integration point

New decision: does fixed100000 board quantization preserve the old FULL shared
hand box, rather than only hP=hR=1? Reuse saved complete43-leaf tree; construct
features from decoded physical states, feed quantized board fractions into
the existing exact affine minimizer. Same hP,hR∈[0,1] in every leaf, no independent
leaf boxes. Freeze box certificate before a game search; all branch minima
must be globally certified and best/full ties identical to exact saved contact.

Then ONE new production qdepth0/depth2 search at hP=hR=0, no ordering/TT/native/
tactical. Subclass frozen evaluator replaces only the global held term; board
coefficients, scale, terminal handling, root/history and search semantics fixed.
Compare exact quantized full reference, all visited physical states and full
ties. Reuse old h=1 contact row, never rerun it. Zero HAND is not zero evaluator:
board weights stay fixed, and neither endpoint is an admitted hand price.

Whole paired128 pushes includes49 saved h=1 pushes; conservative5000 enumeration
includes old whole1130;15sec includes old0.125sec. Use old producer instrumented
callbacks, bind saved tree by explicit path after adding dependency pins. One
point only, no all-endpoint game search, third law or depth increase. Entire
continuous hand-box result comes from exact saved-tree arithmetic, NOT from
sampling endpoints or this one empirical search. No new public goal labels.

Report score change separately from choice stability. Physical held/base
identity remains; hand discount does not change actual legal actions/hands.
Require complete depth/no fallback/qnodes0, balanced push/pop and all inputs
unchanged. Stop on any mismatched proof, state, choice or original resource cap.
