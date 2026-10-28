from scripts.leaper_empty_geometry_signature import empty_geometry_signature
from generic_chess.core.movement import LeapAtom,RayAtom
from generic_chess.core.pieces import PieceType,Piece
from generic_chess.rules.schema import RuleSet
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.session.session import GameSession

def meta(atoms):return {'piece_types':[{'is_anchor':False,'movement_atoms':atoms}]}

def test_one_step_ray_and_leap_have_same_projection():
    assert empty_geometry_signature(meta([{'kind':'ray','direction':[1,0],'max_steps':1}]))==empty_geometry_signature(meta([{'kind':'leap','offset':[1,0]}]))

def test_blocked_ray_collision_is_not_actual_movement_equivalence():
    ray=meta([{'kind':'ray','direction':[1,0],'max_steps':2}]);leaps=meta([{'kind':'leap','offset':[1,0]},{'kind':'leap','offset':[2,0]}]);assert empty_geometry_signature(ray)==empty_geometry_signature(leaps)
    outcomes=[];king=tuple(LeapAtom((x,y)) for x in (-1,0,1) for y in (-1,0,1) if (x,y)!=(0,0))
    for movement in [(RayAtom((1,0),2),),(LeapAtom((1,0)),LeapAtom((2,0)))]:
        board=[[None]*4 for _ in range(4)]
        for owner,tid,x,y in [(0,'K',3,0),(1,'K',3,3),(0,'A',0,0),(0,'Z',1,0)]:board[y][x]=Piece(owner,tid,tid)
        types=(PieceType('K','K',king,is_anchor=True),PieceType('A','A',movement),PieceType('Z','Z',(LeapAtom((4,4)),)))
        rule=RuleSet(schema_version=1,piece_types=types,board_size=4,initial_position=tuple(tuple(r) for r in board),drop_allowed={t:((False,)*16,)*2 for t in ('A','Z')},capture_disposition='remove_from_game',max_ply=96,repetition_limit=4);c=compile_legacy_ruleset_for_semantic_execution(rule);s=GameSession(c);outcomes.append(any(a.from_square.file==0 and a.from_square.rank==0 and a.to_square.file==2 and a.to_square.rank==0 for a in s.legal_actions()))
    assert outcomes==[False,True]

def test_offboard_offsets_do_not_manufacture_empty_board_novelty():
    assert empty_geometry_signature(meta([{'kind':'leap','offset':[1,0]},{'kind':'leap','offset':[40,17]}]))==empty_geometry_signature(meta([{'kind':'leap','offset':[1,0]}]))
