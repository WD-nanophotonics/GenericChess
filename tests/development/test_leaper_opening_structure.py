"""Core counterexamples delimit the structural opening sufficient condition."""
import copy,gzip,json
from pathlib import Path
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.session.session import GameSession
from scripts.leaper_opening_structure import structural_opening_witness

def build(*,mixed=False,maxply=96,far=False,rule_only=False):
    r=json.loads(gzip.decompress(Path('docs/research/data/leaper_root_order_quality_20261026/prepared-v2/inputs.json.gz').read_bytes()))['rows'][0]['RuleSet'];r=copy.deepcopy(r);r.pop('initial_setup_options',None);n=8;r.update(board_size=n,max_ply=maxply,initial_position=[[None]*n for _ in range(n)],metadata={},promotion_allowed={},promotion_forced={})
    king=[(x,y) for x in (-1,0,1) for y in (-1,0,1) if (x,y)!=(0,0)];w=[(-1,0),(1,0),(0,-1),(0,1)]
    catalog=[('K',king),('W',w),('M',king+[(-2,0)]),('P',[(-5,-3)]),('Z',[(8,8)])] if mixed else [('K',king),('W',w)]
    r['piece_types']=[dict(type_id=t,name=t,is_anchor=t=='K',is_promotable=False,promotion_target_ids=[],movement_atoms=[dict(kind='leap',offset=list(o)) for o in offsets]) for t,offsets in catalog];r['drop_allowed']={t:[[False]*64,[False]*64] for t,_ in catalog if t!='K'}
    places=[(0,'K',6,0),(1,'K',0,3),(0,'M',6 if far else 3,7 if far else 3),(0,'P',6,6),(1,'Z',1,3)] if mixed else [(0,'K',0,3),(1,'K',7,4),(0,'W',1,0),(1,'W',6,7)]
    for owner,tid,x,y in places:r['initial_position'][y][x]=dict(owner=owner,base_type_id=tid,current_type_id=tid,promoted=False)
    if rule_only:return r
    c=compile_legacy_ruleset_for_semantic_execution(ruleset_from_dict(r));return c,GameSession(c)

def test_structural_pairs_imply_Core_nonterminal_after_every_actual_first_action():
    c,s=build();w=structural_opening_witness(s.state,c);assert w['status']=='SUFFICIENT_ONE_PLY_REPLY';before=s.to_record();assert s.legal_actions()
    for a in s.legal_actions():
        child=type(s).replay(c,before);child.submit(a);assert not child.state.terminal_status.is_terminal and child.legal_actions()

def test_mixed_parity_actor_can_mate_despite_four_initial_safe_escape_squares():
    c,s=build(mixed=True);w=structural_opening_witness(s.state,c);assert w['status']=='UNKNOWN' and 'mixes' in w['reason'];a=next(a for a in s.legal_actions() if a.from_square.file==3 and a.from_square.rank==3 and a.to_square.file==1 and a.to_square.rank==3);s.submit(a);assert s.state.terminal_status.is_terminal and s.state.terminal_status.winner==0

def test_clock_boundary_does_not_become_position_only_liveness_claim():
    c,s=build(maxply=1);w=structural_opening_witness(s.state,c);assert w['status']=='UNKNOWN' and 'clock' in w['reason'];s.submit(s.legal_actions()[0]);assert s.state.terminal_status.is_terminal

def test_one_escape_of_each_color_suffices_under_ordinary_parity_motion():
    from generic_chess.rules.schema import RuleSet
    from generic_chess.core.pieces import Piece,PieceType
    from generic_chess.core.movement import LeapAtom
    king=[(x,y) for x in (-1,0,1) for y in (-1,0,1) if (x,y)!=(0,0)];knight=[(x,y) for x in (-2,-1,1,2) for y in (-2,-1,1,2) if abs(x)+abs(y)==3]
    types=tuple(PieceType(type_id=t,name=t,movement_atoms=tuple(LeapAtom(o) for o in offsets),is_anchor=t=='K') for t,offsets in [('K',king),('N',knight),('Z',[(8,8)])]);board=[[None]*8 for _ in range(8)]
    for own,tid,x,y in [(0,'K',7,7),(0,'N',5,2),(1,'K',0,3),(1,'Z',1,3),(1,'Z',0,4),(1,'Z',1,4)]:board[y][x]=Piece(own,tid,tid)
    rule=RuleSet(schema_version=1,board_size=8,piece_types=types,initial_position=tuple(tuple(r) for r in board),drop_allowed={t:((False,)*64,)*2 for t in ('N','Z')},capture_disposition='remove_from_game',max_ply=96,repetition_limit=4);c=compile_legacy_ruleset_for_semantic_execution(rule);s=GameSession(c);w=structural_opening_witness(s.state,c);assert w['status']=='SUFFICIENT_ONE_PLY_REPLY';assert sum(len(v) for v in w['escape_colors'].values())==2
    for a in s.legal_actions():
        t=GameSession.replay(c,s.to_record());t.submit(a);assert not t.state.terminal_status.is_terminal and t.legal_actions()
