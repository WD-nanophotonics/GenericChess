"""Full history and resource semantics of the opt-in development UCI adapter."""
from pathlib import Path
import pytest
from generic_chess.ai.limits import SearchLimits
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.western_chess import build_western_chess_ruleset
from scripts import chess_development as d


@pytest.fixture
def author(monkeypatch):
    root = Path('.local_agent/certificate_source/python-chess')
    if root.exists():
        monkeypatch.syspath_prepend(str(root.resolve()))
    return pytest.importorskip('chess.engine')


@pytest.fixture(scope='module')
def compiled():
    return compile_ruleset_for_execution(build_western_chess_ruleset())


FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'


def test_material_config_gauge_and_scale_are_frozen():
    assert d.material_tables() == {
        'geometric_half': dict(P=208, N=605, B=549, R=1071, Q=1194),
        'linear_mixture': dict(P=208, N=483, B=394, R=767, Q=855),
        'unit': dict.fromkeys('PNBRQ', 208)}


def test_replayed_repetition_is_not_reset_to_fen(compiled, author):
    import chess
    external = d.UciOpponent(None, FEN, 1)
    prefix = ['g1f3', 'g8f6', 'f3g1', 'f6g8']*2
    state, witnesses = d.replay_prefix(FEN, compiled, prefix, (external,))
    assert state.ply_count == 8 and len(state.history) == len(witnesses) == 9
    assert len(external.board.move_stack) == 8
    assert max(v for _, v in state.repetition_counts) == 3
    assert external.board.can_claim_threefold_repetition()


def test_prefix_rejects_illegal_action_and_terminal_continuation(compiled):
    with pytest.raises(ValueError, match='illegal opening'):
        d.replay_prefix(FEN, compiled, ['e2e5'])
    with pytest.raises(ValueError, match='after terminal'):
        d.replay_prefix('7k/6Q1/5K2/8/8/8/8/8 b - - 0 1', compiled, ['h8h7'])


def test_material_transport_has_actual_prefix_and_time_limit(compiled, author):
    import chess
    seen = []
    class Engine:
        def configure(self, options):
            assert options == {'Clear Hash': None}
        def play(self, board, limit, game, info):
            assert board.uci_variant == 'gc_unit'
            assert [m.uci() for m in board.move_stack] == ['e2e4', 'e7e5']
            assert limit.time == .25 and limit.nodes is None and limit.depth is None
            seen.append(game)
            return author.PlayResult(chess.Move.from_uci('g1f3'), None,
                info=dict(score=author.PovScore(author.Cp(17), board.turn), depth=4, nodes=40))
    player = d.UciMaterial(Engine(), FEN, 'unit', .25)
    state, _ = d.replay_prefix(FEN, compiled, ['e2e4', 'e7e5'], (player,))
    move, row = player.choose()
    assert move == 'g1f3' and row['score_cp'] == 17 and row['engine_nodes'] == 40
    assert row['statistics'] == {} and 'not complete fixed-depth' in row['search_completion_scope']
    assert state.ply_count == 2 and len(seen) == 1


def test_two_uci_players_advance_together_and_illegal_choice_stays_unplayed(compiled, author):
    import chess
    class Engine:
        def configure(self, _): pass
        def play(self, board, limit, game, info):
            return author.PlayResult(chess.Move.from_uci('e2e5'), None)
    local = d.UciMaterial(Engine(), FEN, 'unit', .25)
    external = d.UciOpponent(Engine(), FEN, 1)
    result = d.play_game(FEN, compiled, 'unit', 'uci_reference',
        SearchLimits(max_depth=2, max_nodes=20, max_time_seconds=1), 2,
        external=external, local_external=local, prefix=['e2e4', 'e7e5'])
    assert result['end'] == 'execution_failure' and result['plies_played'] == 0
    assert len(local.board.move_stack) == len(external.board.move_stack) == 2
    assert len(result['final_state']['history']) == 3


def test_reference_prefix_cannot_reuse_fresh_fen_cache(tmp_path, monkeypatch, author):
    import hashlib, json
    seen = []
    class Engine:
        id = {'name':'prefix-history fixture'}
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def configure(self, options): assert options == {'Threads':1,'Hash':16}
        def analyse(self, child, limit, game):
            assert [m.uci() for m in child.move_stack] == ['e2e4','e7e5','g1f3']
            seen.append(child.fen())
            return dict(score=author.PovScore(author.Cp(12),child.turn),nodes=30,depth=2)
    monkeypatch.setattr(author.SimpleEngine,'popen_uci',lambda *a,**k:Engine())
    case=dict(id='prefix',fen=FEN,opening_uci=['e2e4','e7e5'],accepted_uci=['g1f3'])
    suite=tmp_path/'suite.json';suite.write_text(json.dumps(dict(scope='transport only',cases=[case])))
    saved=tmp_path/'compare.json';saved.write_text(json.dumps({'cases':[dict(case,rows=[dict(move='g1f3',completed=True)])]}))
    engine=tmp_path/'inert';engine.write_bytes(b'never executed')
    cache=tmp_path/'cache.json';cache.write_text(json.dumps({'binary_sha256':hashlib.sha256(engine.read_bytes()).hexdigest(),
        'conditions':dict(threads=1,hash_mib=16,nodes_per_child=50000,fresh_game_each_child=True),
        'cases':[dict(fen=FEN,references={'g1f3':dict(cp=999)})]}))
    output=tmp_path/'out.json'
    d.main(['reference','--suite',str(suite),'--comparison',str(saved),'--output',str(output),
            '--engine',str(engine),'--reference-cache',str(cache)])
    report=json.loads(output.read_bytes());assert len(seen)==1
    assert report['new_analyses']==1 and report['cached_analyses']==0
    assert report['cases'][0]['references']['g1f3']['cp']==-12


def test_material_compare_keeps_policy_and_history(compiled, author):
    import chess
    seen=[]
    class Engine:
        def configure(self, options): assert options=={'Clear Hash':None}
        def play(self, board, limit, game, info):
            seen.append((board.uci_variant,len(board.move_stack)))
            return author.PlayResult(chess.Move.from_uci('g1f3'),None,
                info=dict(score=author.PovScore(author.Cp(7),board.turn),nodes=9))
    case=dict(id='prefix',fen=FEN,opening_uci=['e2e4','e7e5'],accepted_uci=['g1f3'],
              answer_basis='transport fixture, not tactical truth')
    result=d.compare_material_case(case,compiled,Engine(),.25)
    assert seen==[('gc_'+policy,2) for policy in d.POLICIES]
    assert all(r['legal'] and r['state_preserved'] for r in result['rows'])
    assert all(r['reference_hit'] for r in result['rows'])


def test_shifted_material_config_fails_before_execution(tmp_path, monkeypatch, author):
    import json
    monkeypatch.setattr(author.SimpleEngine,'popen_uci',lambda *a,**k:pytest.fail('invalid config must not execute'))
    suite=tmp_path/'suite.json';suite.write_text(json.dumps(dict(scope='config guard',cases=[dict(id='fresh',fen=FEN,accepted_uci=['e2e4'])])))
    config=tmp_path/'material.ini';config.write_text(d.material_config_text().replace('p:208','p:209'))
    engine=tmp_path/'inert';engine.write_bytes(b'not executable')
    out=tmp_path/'out.json'
    with pytest.raises(SystemExit) as exc:
        d.main(['compare','--suite',str(suite),'--output',str(out),'--material-engine',str(engine),'--material-config',str(config)])
    assert exc.value.code==2 and not out.exists()


def test_material_summary_does_not_turn_unknown_resources_into_zero():
    rows=[dict(policy=p,completed=True,reference_hit=True,move='g1f3',
               controller_cpu_seconds=.01,engine_nodes=20,statistics={}) for p in d.POLICIES]
    methods=d.comparison_summary([dict(rows=rows)])['methods']
    assert all(m['cpu_seconds'] is None and m['nodes'] is None for m in methods.values())
    assert all(m['controller_cpu_seconds']==.01 and m['engine_nodes']==20 for m in methods.values())


def test_multipv_uses_final_bestmove_not_stale_highest_score(compiled, author):
    import chess
    class Analysis:
        multipv = [dict(multipv=1, pv=[chess.Move.from_uci('g1f3')],
                         score=author.PovScore(author.Cp(17), chess.WHITE), depth=8, nodes=90),
                   dict(multipv=2, pv=[chess.Move.from_uci('b1c3')],
                         score=author.PovScore(author.Cp(900), chess.WHITE), depth=7, nodes=80)]
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def wait(self): return author.BestMove(chess.Move.from_uci('g1f3'), None)
    class Engine:
        def configure(self, options): assert options == {'Clear Hash': None}
        def play(self, *args, **kwargs): pytest.fail('MultiPV must await analysis bestmove')
        def analysis(self, board, limit, *, multipv, game):
            assert multipv == 3 and limit.time == .25
            assert [m.uci() for m in board.move_stack] == ['e2e4', 'e7e5']
            return Analysis()
    player = d.UciMaterial(Engine(), FEN, 'unit', .25, multipv=3)
    d.replay_prefix(FEN, compiled, ['e2e4', 'e7e5'], (player,))
    move, row = player.choose()
    assert move == 'g1f3' and row['score_cp'] == 17 and row['engine_depth'] == 8
    assert row['engine_nodes'] == 90 and row['multipv'] == 3
    assert row['multipv_lines'][1]['score_cp'] == 900
    assert 'pv' not in row['multipv_lines'][1]  # Only selected full PV is stored.


def test_multipv_missing_info_preserves_unknown_costs(author):
    import chess
    class Analysis:
        multipv = []
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def wait(self): return author.BestMove(chess.Move.from_uci('e2e4'), None)
    class Engine:
        def configure(self, options): pass
        def analysis(self, *args, **kwargs): return Analysis()
    move, row = d.UciMaterial(Engine(), FEN, 'unit', .25, multipv=3).choose()
    assert move == 'e2e4' and row['pv'] == [] and row['score_cp'] is None
    assert row['engine_nodes'] is None and row['engine_seconds'] is None
