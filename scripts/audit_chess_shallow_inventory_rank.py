"""Count material-balance variation in shallow initial Chess histories."""

from collections import Counter
from pathlib import Path
import sys
from time import monotonic


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from generic_chess.core.transition import initial_state, legal_successors
from scripts.audit_f24f_western_chess_perft import standard_engine


TYPES = ("P", "N", "B", "R", "Q")
MAX_HISTORIES = 10_000
MAX_SECONDS = 30


def balance(state):
    counts = Counter((piece.owner, piece.current_type_id)
                     for piece in state.position.board if piece is not None)
    return tuple(counts[(0, type_id)] - counts[(1, type_id)] for type_id in TYPES)


def audit():
    compiled, _ = standard_engine()
    frontier = [initial_state(compiled)]
    started = monotonic()
    layers = []
    for depth in range(4):
        vectors = Counter(balance(state) for state in frontier)
        layers.append({"depth": depth, "histories": len(frontier),
                       "distinct_balance_vectors": len(vectors),
                       "balance_counts": {str(vector): count
                                          for vector, count in sorted(vectors.items())}})
        if depth == 3:
            break
        next_frontier = []
        for state in frontier:
            if monotonic() - started > MAX_SECONDS:
                raise TimeoutError("initial Chess inventory audit time budget exceeded")
            next_frontier.extend(child for _, child in legal_successors(state, compiled))
            if len(next_frontier) > MAX_HISTORIES:
                raise RuntimeError("initial Chess inventory audit history cap exceeded")
        frontier = next_frontier
    return {"types": TYPES, "layers": layers,
            "elapsed_seconds": monotonic() - started}


if __name__ == "__main__":
    import json
    print(json.dumps(audit(), indent=2))
