# Material policy tuning and extracted values
Beal and Smith (1997) report learning chess piece values with temporal differences applied to minimax, with values competitive against textbook controls. Only the publisher abstract was accessible here; its detailed settings and cost were not verified. [Publisher abstract](https://journals.sagepub.com/doi/abs/10.3233/ICG-1997-20302).

McGrath et al. (2022) extract material weights by fitting a tanh linear model of piece-count differences to AlphaZero's value head. That is descriptive extraction from a learned nonlinear evaluator, not direct optimization of a fixed material-only policy. The authors explicitly separate correlation from causation. [Primary paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC9704706/).

Our inference: neither result licenses replacing true outcomes by material-count wins, nor proves that this mature material-only experiment must work quickly. Retain fixed training distributions and independent policy utility. These sources were read after current candidate prices were frozen; no human weights, game database or neural labels were imported, and no Xiangqi holdout was inspected.
