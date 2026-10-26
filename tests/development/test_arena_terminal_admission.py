"""Completed pair progress must not score an ongoing prefix; no search or games."""
from dataclasses import replace
import json
import pytest
from generic_chess.learning import arena as A
from generic_chess.learning.openings import ArenaOpening, ArenaOpeningCorpus
from generic_chess.learning.material import LearnableMaterialCheckpoint
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.core.identity import position_identity_key
from generic_chess.session.session import GameSession
from generic_chess.learning.serialization import stable_sha256
from native_test_helpers import generated_compiled


def ongoing_game():
    return A.ArenaGameResult(pair=0,opening_id='root',opening_position_key='root',
        child_owner=0,winner=None,result='ongoing',plies=0,actions=(),final_position_key='root')


def test_ongoing_prefix_is_not_a_scoring_draw():
    game=ongoing_game()
    assert game.is_scoring_result is False
    assert game.child_points is None
    pair=A.ArenaPairResult(0,'root',game,replace(game,child_owner=1))
    assert pair.child_pair_score is None


def test_pair_resume_rejects_replayable_ongoing_progress_before_search(tmp_path,monkeypatch):
    compiled=generated_compiled(size=4,seed=7)
    root=GameSession(compiled)
    assert root.result.status.value=='ongoing'
    key=position_identity_key(root.state.position,compiled)
    openings=ArenaOpeningCorpus(ruleset_fingerprint=compiled.ruleset_fingerprint,
        min_plies=0,max_plies=0,openings=(ArenaOpening(0,1,0,(),key),))
    profile=build_ruleset_profile(compiled,EvaluationConfig())
    cp=LearnableMaterialCheckpoint.from_profile(compiled,profile,training_seed=1)
    config=A.ArenaConfig(pairs=1)
    identity=A._progress_identity(compiled,cp,cp,config,openings)
    identity_hash=stable_sha256(identity)
    game=replace(ongoing_game(),opening_id=key,opening_position_key=key,final_position_key=key)
    pair=A.ArenaPairResult(0,key,game,replace(game,child_owner=1))
    manifest={'schema':A.ARENA_PROGRESS_SCHEMA,'identity_sha256':identity_hash,'identity':identity}
    (tmp_path/'manifest.json').write_text(json.dumps(manifest),encoding='utf-8')
    (tmp_path/'pair-000000.json').write_text(json.dumps(A._pair_to_dict(pair,identity_hash)),encoding='utf-8')
    monkeypatch.setattr(A,'_play_pair',lambda *args,**kwargs:pytest.fail('progress validation launched a game'))
    monkeypatch.setattr(A,'_engine_for',lambda *args,**kwargs:pytest.fail('progress validation built an engine'))
    with pytest.raises(A.ArenaExecutionError,match='does not replay|terminal'):
        A.run_arena_resumable(compiled,None,cp,cp,config,progress_dir=tmp_path,openings=openings)


@pytest.mark.parametrize('status,winner,points', [
    ('max_ply',None,.5),('repetition',None,.5),
    ('checkmate',0,1.),('checkmate',1,0.),
    ('no_contest',None,None),('declaration',None,None),
    ('declaration',0,1.)])
def test_actual_scoring_and_non_scoring_result_contracts_remain(status,winner,points):
    game=replace(ongoing_game(),result=status,winner=winner)
    assert game.child_points==points



def test_pair_resume_accepts_actual_rule_terminal_without_search(tmp_path,monkeypatch):
    from conftest import make_compiled, king_type
    compiled=make_compiled(4,[king_type()],max_ply=1)
    root=GameSession(compiled)
    key=position_identity_key(root.state.position,compiled)
    action=root.legal_actions()[0]
    root.submit(action)
    assert root.result.status.value=='max_ply'
    openings=ArenaOpeningCorpus(ruleset_fingerprint=compiled.ruleset_fingerprint,
        min_plies=0,max_plies=0,openings=(ArenaOpening(0,1,0,(),key),))
    cp=LearnableMaterialCheckpoint(ruleset_fingerprint=compiled.ruleset_fingerprint)
    config=A.ArenaConfig(pairs=1)
    identity=A._progress_identity(compiled,cp,cp,config,openings)
    identity_hash=stable_sha256(identity)
    game=replace(ongoing_game(),opening_id=key,opening_position_key=key,
        final_position_key=position_identity_key(root.state.position,compiled),
        result=root.result.status.value,winner=root.result.winner,plies=1,actions=(action,))
    pair=A.ArenaPairResult(0,key,game,replace(game,child_owner=1))
    (tmp_path/'manifest.json').write_text(json.dumps({
        'schema':A.ARENA_PROGRESS_SCHEMA,'identity_sha256':identity_hash,'identity':identity}),encoding='utf-8')
    (tmp_path/'pair-000000.json').write_text(json.dumps(A._pair_to_dict(pair,identity_hash)),encoding='utf-8')
    monkeypatch.setattr(A,'_play_pair',lambda *args,**kwargs:pytest.fail('completed progress launched a game'))
    monkeypatch.setattr(A,'_engine_for',lambda *args,**kwargs:pytest.fail('completed progress built an engine'))
    summary=A.run_arena_resumable(compiled,None,cp,cp,config,progress_dir=tmp_path,openings=openings)
    assert summary.pair_count==1 and summary.mean_pair_score==.5
    assert summary.game_draws==2
