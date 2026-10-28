"""Constructive recipe has a real Core consumer on a separate small control."""
from scripts.leaper_structural_layout import layout
from scripts.leaper_opening_structure import structural_opening_witness
from test_leaper_opening_structure import build
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.session.session import GameSession

def test_constructed_literal_recipe_passes_structural_and_Core_first_reply():
    c,s=build();types=[{'type_id':t.type_id,'is_anchor':t.is_anchor,'movement_atoms':[{'kind':'leap','offset':list(a.offset)} for a in t.movement_atoms]} for t in c.piece_types];p=layout(types);assert p['status']=='GEOMETRY_LAYOUT_ONLY'
    from generic_chess.core.pieces import Piece
    board=[[None]*8 for _ in range(8)]
    for a in p['placements']:
        x,y=a['square'];board[y][x]=Piece(a['owner'],a['type'],a['type'])
    # Recompile a complete RuleSet; metadata output alone did not prove admission.
    # Use explicit original rule from fixture's compiled inspection: construct anew.
    from generic_chess.rules.schema import RuleSet
    rule=RuleSet(schema_version=1,piece_types=c.piece_types,board_size=8,initial_position=tuple(tuple(r) for r in board),drop_allowed={'W':((False,)*64,)*2},capture_disposition='remove_from_game',max_ply=96,repetition_limit=4)
    cc=compile_legacy_ruleset_for_semantic_execution(rule);ss=GameSession(cc);assert structural_opening_witness(ss.state,cc)['status']=='SUFFICIENT_ONE_PLY_REPLY'
    for a in ss.legal_actions():
        t=GameSession.replay(cc,ss.to_record());t.submit(a);assert not t.state.terminal_status.is_terminal and t.legal_actions()

def test_recipe_rejects_mixed_parity_without_seed_or_outcome_replacement():
    c,s=build(mixed=True);types=[{'type_id':t.type_id,'is_anchor':t.is_anchor,'movement_atoms':[{'kind':'leap','offset':list(a.offset)} for a in t.movement_atoms]} for t in c.piece_types]
    types=[t for t in types if t['type_id'] in ('K','M')]
    x=layout(types,parity_only=True);assert x['status']=='UNSUPPORTED' and 'parity' in x['reason']
    assert layout(types)['status']=='GEOMETRY_LAYOUT_ONLY'
