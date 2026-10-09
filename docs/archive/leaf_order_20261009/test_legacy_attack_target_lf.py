"""Target query preserves full-map semantics across actual generated histories."""
import pytest
from generic_chess.core.attacks import is_square_attacked, pseudo_attacks
from generic_chess.core.coordinates import index_to_square, Square
from generic_chess.generation.config import GeneratorConfig
from generic_chess.generation.generator import generate_game
from generic_chess.session.session import GameSession


@pytest.mark.parametrize('size,seed', [(4,7), (4,21), (6,7), (6,21)])
def test_target_query_matches_full_map_after_actual_moves(size, seed):
    generated = generate_game(GeneratorConfig(seed=seed, board_size=size,
        setup_preset='bilateral_random', allow_hybrid=True))
    compiled = generated.compiled_ruleset
    session = GameSession(compiled)
    for _ in range(6):
        before = session.state
        for owner in (0, 1):
            expected = pseudo_attacks(before.position, owner, compiled)
            for index in range(size * size):
                square = index_to_square(index, size)
                assert is_square_attacked(before.position, square, owner, compiled) == (square in expected)
            assert not is_square_attacked(before.position, Square(-1, 0), owner, compiled)
            assert not is_square_attacked(before.position, Square(size, size), owner, compiled)
        assert session.state == before
        actions = session.legal_actions()
        if not actions:
            break
        session.submit(sorted(actions, key=str)[0])
