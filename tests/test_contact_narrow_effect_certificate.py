from dataclasses import replace
from fractions import Fraction as F
import hashlib,json
from pathlib import Path
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.western_chess import build_western_chess_ruleset
from generic_chess.core.semantic_executor import semantic_engine_for
from scripts.research_state_replay import read_game_state
ROOT=Path(__file__).resolve().parents[1]
def read(name):return json.loads((ROOT/'docs/research/data'/name).read_text())
def test_all122_projected_king_escape_witnesses_match_compiled_attack_semantics():
    r=read('contact_narrow_effect_qualified_20261005.json');raw=read('contact_narrow_width_20261005.json')
    engine=semantic_engine_for(compile_ruleset_for_execution(build_western_chess_ruleset()))
    count=0
    for row,old in zip(r['rows'],raw['rows']):
        assert set(row['branches'])==set(old['all_root_actions'])
        for key,leaves in row['branches'].items():
            p=read_game_state(old['branches'][key]['state']).position
            assert [x['action'] for x in leaves]==old['branches'][key]['all_enemy_actions']
            for leaf in leaves:
                board=list(p.board);src,dst=leaf['source'],leaf['target'];piece=board[src]
                assert piece.owner==1 and piece.current_type_id==leaf['actor']
                assert leaf['removed_knight']==(board[dst] is not None)
                board[src]=None;board[dst]=piece
                king=next(i for i,x in enumerate(board) if x and x.owner==0 and x.current_type_id=='K')
                escape=leaf['king_escape']
                assert max(abs(king%8-escape%8),abs(king//8-escape//8))==1
                assert board[escape] is None or board[escape].owner==1 and board[escape].current_type_id=='R'
                board[escape]=board[king];board[king]=None
                after=replace(p,board=tuple(board),side_to_move=0)
                assert not engine.in_check(after,0);count+=1
    assert count==122 and r['complete'] and r['analytic_reply_effects']==122

def test_complete_static_ties_and_raw_failure_are_preserved():
    r=read('contact_narrow_effect_qualified_20261005.json')
    assert r['charged_public_transitions']==8 and r['charged_enumerated_actions']==162
    assert r['new_public_transitions']==r['new_enumerated_actions']==r['source_queries']==0
    for row in r['rows']:
        for law in ('geometric_half','linear_mixture','unit'):
            model=row['models'][law]
            assert len(model['scores'])==4 and len(model['tie_set'])==3
            assert all('k_quiet' in key for key in model['tie_set'])
            assert set(model['tie_set'])==set(row['models']['unit']['tie_set'])
            numeric=list(map(F,model['scores'].values()))
            assert min(numeric)<max(numeric)
        assert len(row['models']['zero']['tie_set'])==4
    failed=read('contact_narrow_effect_certificate_20261005.json')
    assert not failed['complete'] and 'ply' in failed['error'] and not failed['rows'][0]['branches']
    for report in (r,failed):
        for path,pin in report['source_sha256'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==pin
