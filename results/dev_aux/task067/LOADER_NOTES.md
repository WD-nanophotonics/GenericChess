# Standalone loading boundary

The initial neutral-module import succeeded, as did four rejection controls, but its first search failed before C search with ImportError: relative import has no known parent package. The artifact retains product relative imports. Load the auxiliary class under generic_chess.native._aux_binding so those imports resolve to the frozen package; this changes only the loader namespace, not candidate bytes, inputs or limits. Failure retained; no success checkpoint recorded.
