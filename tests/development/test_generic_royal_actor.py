"""Sized independent controls agree on every generated public successor."""
import random
import pytest
from scripts.generic_royal_actor import RoyalActor
from scripts.generic_proof_rnb_bridge import compile_rnb,from_actor,actor_state,uci
from generic_chess.core.movegen import legal_actions
from generic_chess.core.transition import apply_action


@pytest.mark.parametrize('width',[4,5,8])
def test_sized_actor_all_generated_legal_frontiers(width):
    rng=random.Random(2026101555+width);model=RoyalActor(width);c=compile_rnb(width);checked=0
    while checked<24:
        board=['.']*(width*width)
        for i,p in zip(rng.sample(range(len(board)),6),'KkRNrn'):board[i]=p
        raw=tuple(board)+(0,)
        if not model.valid(raw):continue
        state=from_actor(c,raw)
        public={uci(a):actor_state(apply_action(state,a,c)) for a in legal_actions(state,c)}
        assert public==dict(model.moves(raw));checked+=1
        for child in public.values():assert model.valid(child)


def test_bad_dimensions_and_unsupported_piece_are_rejected():
    for w in (0,2,9,True):
        with pytest.raises(ValueError):RoyalActor(w)
    assert not RoyalActor(4).valid(tuple('KkP'+'.'*13)+(0,))
