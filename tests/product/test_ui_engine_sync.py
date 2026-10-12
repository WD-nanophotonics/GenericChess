"""Production sync identity, historical Shogi continuation and new terminal rules."""
from dataclasses import replace
import json
from pathlib import Path

from generic_chess.core.pieces import Piece
from generic_chess.core.position import Hands
from generic_chess.core.terminal import TerminalStatus, terminal_result
from generic_chess.rules.catalog import build_builtin_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import serialize_ruleset
from generic_chess.session import GameSession
from generic_chess.ui.ai_backend import ENGINE_BASE_SHA, create_ui_player
from generic_chess.ui.material_values import human_material_profile
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ui.web.app import create_app
from generic_chess.ui.web.models import GameConfig
from generic_chess.ui.web.service import GameService


def test_engine_version_matches_pinned_source(tmp_path):
    root=Path(__file__).resolve().parents[2]
    assert json.loads((root/'docs/ui/AI_BASELINE.json').read_text())['product_base_sha']==ENGINE_BASE_SHA
    from fastapi.testclient import TestClient
    with TestClient(create_app(tmp_path)) as client:
        assert client.get('/api/health').json()['engine_sha']==ENGINE_BASE_SHA
        state=client.post('/api/games',json={'config':{'kind':'western_chess','mode':'pvp'}}).json()
        assert state['ai']['engine_sha']==ENGINE_BASE_SHA
        assert state['ai']['backend'].startswith('Core q4')


def test_original_shogi_save_keeps_rules_record_and_human_prices(tmp_path):
    rules=replace(build_builtin_ruleset('standard_shogi'),stalemate_result='draw')
    service=GameService(tmp_path)
    try:
        game=service.create(GameConfig(kind='standard_shogi',mode='pvp'))
        ctrl,config,paused=game.imported('rules',serialize_ruleset(rules))
        ctrl.submit_action(ctrl.session.legal_actions()[0])
        record=ctrl.record_text()
        # Same public rule+record roundtrip as restored bundles.
        recovered,config,paused=game.imported('bundle',{
            'schema':'generic-chess-web-v1','config':config.model_dump(),
            'rules':json.loads(serialize_ruleset(rules)),'record':json.loads(record),'paused':True})
        assert recovered.session.state==ctrl.session.state
        assert recovered.ruleset.stalemate_result=='draw'
        assert create_ui_player(recovered.compiled,use_disk_cache=False).evaluation_profile.board_value_by_type['TP']==7000
    finally:
        service.executor.shutdown(wait=True)


def test_new_shogi_no_move_is_loss_without_learning_dependencies():
    rules=build_builtin_ruleset('standard_shogi')
    assert rules.stalemate_result=='loss'
    compiled=compile_ruleset_for_execution(rules)
    state=GameSession(compiled).state
    board=[None]*81
    board[8*9+0]=Piece(1,'K','K')
    board[0*9+8]=Piece(0,'K','K')
    board[6*9+1]=Piece(0,'R','TR',True)
    position=replace(state.position,board=tuple(board),hands=(Hands((('G',1),)),Hands.empty()),side_to_move=1)
    result=terminal_result(replace(state,position=position),compiled)
    assert result.status is TerminalStatus.STALEMATE
    assert result.winner==0
