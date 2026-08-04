"""A small command-line demo used to verify the engine (not a UI).

It generates one fixed-seed 8x8 ``classic_like`` game, prints the fingerprint,
piece types, promotion/drop summaries and the initial board, then plays up to
50 random plies while asserting the system invariants on every ply.

Run with::

    python -m generic_chess.demo.headless_demo
"""

from __future__ import annotations

import random

from ..core.actions import BoardMove, DropMove
from ..core.attacks import anchor_square
from ..core.coordinates import Square, index_to_square, square_to_index, square_str
from ..core.movegen import legal_actions
from ..core.position import count_entities
from ..core.transition import apply_action, initial_state
from ..generation.config import GeneratorConfig
from ..generation.generator import generate_game
from ..rules.compiler import compile_ruleset
from ..rules.serialization import deserialize_ruleset, serialize_ruleset


DEMO_SEED = 2026
DEMO_PLIES = 50


def check_invariants(position: Position, compiled, initial_count: int) -> list[str]:
    """Assert the system invariants; return a list of problems (empty = ok)."""
    problems: list[str] = []
    if count_entities(position) != initial_count:
        problems.append(
            f"entity conservation violated: {count_entities(position)} != {initial_count}"
        )
    for player in (0, 1):
        count = sum(
            1
            for p in position.board
            if p is not None
            and p.owner == player
            and compiled.types_by_id[p.current_type_id].is_anchor
        )
        if count != 1:
            problems.append(f"player {player} has {count} anchors (expected 1)")
        sq = anchor_square(position, player, compiled)
        if sq is None:
            problems.append(f"player {player} anchor missing")
    return problems


def render_board(position: Position, n: int) -> str:
    lines = []
    lines.append("  " + " ".join(square_str(Square(f, 0))[0] for f in range(n)))
    for rank in range(n - 1, -1, -1):
        cells = []
        for file in range(n):
            piece = position.board[square_to_index(Square(file, rank), n)]
            if piece is None:
                cells.append(".")
            else:
                tid = piece.current_type_id
                cells.append(("+" if piece.promoted else "") + tid)
        lines.append(f"{rank + 1:>2} " + " ".join(f"{c:>2}" for c in cells))
    return "\n".join(lines)


def _promotion_summary(compiled) -> str:
    n = compiled.board_size
    parts = []
    for pt in compiled.piece_types:
        if not pt.is_promotable:
            continue
        zone = [idx for idx in range(n * n) if not compiled.empty_forward_mobility[pt.type_id][0][idx]]
        forced = [idx for idx in range(n * n) if not compiled.empty_mobility[pt.type_id][0][idx]]
        parts.append(
            f"{pt.type_id}: zone={len(zone)} squares, forced={len(forced)} squares, "
            f"targets={','.join(pt.promotion_target_ids) or 'none'}"
        )
    return "\n".join(parts) if parts else "none"


def _drop_summary(compiled) -> str:
    n = compiled.board_size
    parts = []
    for pt in compiled.piece_types:
        if pt.is_anchor:
            continue
        allowed = sum(1 for b in compiled.drop_allowed[pt.type_id][0] if b)
        parts.append(f"{pt.type_id}: drop allowed on {allowed}/{n * n} squares")
    return "\n".join(parts)


def main() -> int:
    print("=" * 68)
    print("GenericChess v0 headless demo (no UI)")
    print("=" * 68)

    cfg = GeneratorConfig(seed=DEMO_SEED)
    game = generate_game(cfg)
    compiled = game.compiled_ruleset
    n = compiled.board_size
    initial_count = compiled.initial_entity_count

    print(f"\nseed:                {DEMO_SEED}")
    print(f"preset:              {cfg.setup_preset}")
    print(f"board:               {n}x{n}")
    print(f"generation attempts: {game.generation_report.generation_attempts}")
    print(f"ruleset fingerprint: {compiled.ruleset_fingerprint}")

    print("\n-- piece types --")
    for rep in game.generation_report.piece_type_reports:
        print(
            f"  {rep.type_id:>2} ({rep.name:<8}) promotable={rep.is_promotable} "
            f"atoms={len(rep.movement_atoms)} avg_mobility={rep.average_mobility:.2f}"
        )
        for atom in rep.movement_atoms:
            print(f"      {atom}")

    print("\n-- promotion summary (player 0 perspective) --")
    print(_promotion_summary(compiled))
    print("\n-- drop summary (player 0 perspective) --")
    print(_drop_summary(compiled))

    print("\n-- initial position (top = player 1 side) --")
    print(render_board(compiled.initial_position, n))

    # Serialization sanity before play.
    round_tripped = deserialize_ruleset(serialize_ruleset(game.ruleset))
    compiled_rt = compile_ruleset(round_tripped)
    print(f"\nserialization round-trip fingerprint stable: "
          f"{compiled_rt.ruleset_fingerprint == compiled.ruleset_fingerprint}")

    state = initial_state(compiled)
    rng = random.Random(DEMO_SEED + 1)
    print(f"\n-- playing up to {DEMO_PLIES} random plies (rng seed {DEMO_SEED + 1}) --")
    for ply in range(1, DEMO_PLIES + 1):
        problems = check_invariants(state.position, compiled, initial_count)
        if problems:
            print("INVARIANT FAILURE:", problems)
            return 1
        actions = legal_actions(state, compiled)
        if not actions:
            break
        action = rng.choice(actions)
        state = apply_action(state, action, compiled)
        label = str(action)
        print(f"  ply {ply:>3}: {label:<16} terminal={state.terminal_status}")
        if state.terminal_status.is_terminal:
            break
    else:
        print(f"  reached demo ply limit of {DEMO_PLIES} (game still ongoing)")

    print("\n-- final board --")
    print(render_board(state.position, n))
    print(f"\nfinal status: {state.terminal_status}")
    print("demo finished cleanly")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
