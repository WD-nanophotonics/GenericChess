# H50 F49 semantic learning re-entry results

Date: 2026-09-03  
Parent checkpoint: `109122bbf8d593fc76ba8f5daf0389029b0fbc28`  
Measurement transport: persistent semantic Native search, with exact `GameSession` history replay and fresh checkpoint engines.  
RuleSet fingerprints: Western `7bc6cf3179f4eaea30b205576b9032dca47a16803e9cc8b3e29405cb1e820b35`; Standard Shogi `ac9873cffe75d8fa885ba787c1aa7cf60e92205465bf056b12b2989674007635`; generated `9f7e7201a19f8f0ee6c0eacc766c2ac3a6c313e06bbc960d5d6dfb89137db923`.  
Seeds: training `480700`, holdout `480703`, arena `480708`.

## Result

The semantic Native re-entry completed with no failed Native searches. The registered selector classified the result as `MATERIAL_ONLY_REPRESENTATION_LIMITING`, with next boundary `F50_GENERIC_LEARNABLE_EVALUATOR_EXPANSION`.

The current learnable-material signal is not sufficient to establish a reliable TD learning or playing-strength improvement:

| RuleSet | Stable teacher surface | L49-1 at 2000 nodes | Python non-material control |
| --- | ---: | ---: | --- |
| Western | S49-M only (`0.921875`) | no usable perturbations | valid on S49-M |
| Standard Shogi | F48 control and S49-M (`0.921875`, `0.984375`) | `0.0`, `0.0234375` | valid on stable corpora |
| Generated | none (teacher stability below gate) | not admissible for learning | not run |

L49-0/L49-2 did flip decisions on some stable material corpora (Western S49-M: `0.009375`/`0.134375`; Shogi S49-M: `0.0012019`/`0.0372596`), but the registered learner-aligned L49-1 signal did not meet the usable-signal gate. The non-material control therefore supplied the two RuleSet witnesses for the classification.

Because the pre-registered admissibility gate was not met, `learning_invoked=false` and paired TD child-versus-parent arena measurements were not entered. This is an intentional fail-closed result: no arena score or learning gain is inferred from an inadmissible teacher/material surface.

## Evidence

The complete raw evidence bundle is retained outside Git at `.generic_chess_flow/f49-semantic-reentry-authoritative/f49_evidence_bundle.json`; generated partition files remain transient. The launcher is `scripts/f49_semantic_reentry.py`. The semantic partition identity is kept at `5f08af687b36e65ac8ed94ce0c617b9c527223c5cf9a832df52f805733d37490` so interrupted scheduler-only reruns resume exact measurement partitions.

Promotion disposition: HOLD. The next work should expand the learnable evaluator representation, then re-register a learning/arena experiment with a stable teacher and measurable material leverage.
