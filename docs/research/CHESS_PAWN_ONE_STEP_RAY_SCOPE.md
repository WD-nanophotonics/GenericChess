# One-step ray's vacuous intermediate occupancy predicate

The frozen original compiled projection stopped before geometry preprocessing:
the shared validator requires path_clear for every ray, whereas Western single
Pawn step is a ray with min=max1 and no intermediate squares/path predicate.
Preserve this failure and original adapter unchanged. The separate subclass
permits only no-path rays with min=max1 and every compiled path length<=1.
Validate them as a leap for the occupancy contract only; physical cache still
uses unchanged compiled candidate paths. No long ray, compound effect or state
guard is relaxed. The same EP/double invariant, source contexts and5000/15sec
caps apply, with failed0.031sec charged to cumulative time. No events rerun.
