"""Learning Phase 1.5: evaluator-neutral opening corpus."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest

from generic_chess.learning.openings import (
    ArenaOpeningCorpus,
    generate_arena_openings,
)

from native_test_helpers import generated_compiled


def _setup():
    return generated_compiled(size=4)


def test_same_seed_same_corpus_different_seed_different_corpus():
    compiled = _setup()
    a = generate_arena_openings(compiled, count=8, seed=314159)
    b = generate_arena_openings(compiled, count=8, seed=314159)
    c = generate_arena_openings(compiled, count=8, seed=314160)
    assert a.corpus_id == b.corpus_id
    assert a.corpus_id != c.corpus_id


def test_openings_nonterminal_and_replay_legal():
    compiled = _setup()
    corpus = generate_arena_openings(
        compiled, count=6, seed=314159, min_plies=2, max_plies=6
    )
    corpus.validate(compiled)
    for opening in corpus.openings:
        assert 2 <= len(opening.actions) <= 6


def test_fingerprint_mismatch_rejected():
    compiled = _setup()
    corpus = generate_arena_openings(compiled, count=4, seed=1)
    other = generated_compiled(size=6, seed=11)
    with pytest.raises(ValueError):
        corpus.validate(other)


def test_serialization_roundtrip():
    compiled = _setup()
    corpus = generate_arena_openings(compiled, count=6, seed=314159)
    restored = ArenaOpeningCorpus.from_dict(corpus.to_dict())
    assert restored.corpus_id == corpus.corpus_id
    assert restored.to_dict() == corpus.to_dict()


def test_corpus_independent_of_checkpoint():
    from generic_chess.ai.evaluation.config import EvaluationConfig
    from generic_chess.ai.evaluation.profile import build_ruleset_profile
    from generic_chess.learning.material import LearnableMaterialCheckpoint

    compiled = _setup()
    corpus = generate_arena_openings(compiled, count=4, seed=314159)
    profile = build_ruleset_profile(compiled, EvaluationConfig())
    cp_a = LearnableMaterialCheckpoint.from_profile(compiled, profile)
    cp_b = LearnableMaterialCheckpoint(
        ruleset_fingerprint=cp_a.ruleset_fingerprint,
        evaluation_profile_version=cp_a.evaluation_profile_version,
        generation=1,
        parent_checkpoint_id=cp_a.checkpoint_id,
        created_at=cp_a.created_at,
        board_weights={k: v + 5 for k, v in cp_a.board_weights.items()},
        hand_weights={k: v + 5 for k, v in cp_a.hand_weights.items()},
        value_scale=cp_a.value_scale,
        reference_median=cp_a.reference_median,
        w_max=cp_a.w_max,
    )
    assert cp_a.checkpoint_id != cp_b.checkpoint_id
    corpus_b = generate_arena_openings(compiled, count=4, seed=314159)
    assert corpus.corpus_id == corpus_b.corpus_id
